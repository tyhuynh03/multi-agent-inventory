import os
import yaml
from typing import Dict, List, Tuple, Union

from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase

from utils.logger import traceable
from db.connection import get_db, run_sql_unified

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

# File này sống trong agents/ nên repo root luôn là cha của cha nó. Đi đường dẫn
# tương đối ("data/metadata_db.yml") chỉ ổn khi tiến trình chạy từ repo root —
# backend/ uvicorn chạy từ backend/, hậu quả là schema rơi về chuỗi fallback 32 ký tự
# và model bịa cột (customer_id, month, product_name).
ROOT_DIR = Path(__file__).resolve().parents[1]


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else ROOT_DIR / path


def load_metadata_yaml(metadata_path: str = "data/metadata_db.yml") -> str:
    """Load database metadata from YAML file and format for prompt"""
    try:
        with open(resolve_repo_path(metadata_path), 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f)
        
        # Format metadata for prompt (full version)
        result = f"**Database:** {metadata['database_description']}\n\n"
        
        for table_name, table_info in metadata['tables'].items():
            result += f"**Table: {table_name}**\n"
            result += f"Description: {table_info['description']}\n\n"
            result += "Columns:\n"
            
            for col in table_info['columns']:
                result += f"- **{col['name']}** ({col['type']}): {col['description']}\n"
            
            result += "\n"
        
        return result
    except Exception as e:
        print(f"Warning: Could not load metadata YAML: {e}")
        return "**Available Tables:** inventory\n"

def get_schema_info(db: SQLDatabase) -> str:
    """Get database schema information for schema-related questions"""
    try:
        tables = db.get_usable_table_names()
        if not tables:
            return "No tables found in the database."
        
        schema_info = f"📋 **Database Schema Information**\n\n"
        schema_info += f"**Available Tables:** {', '.join(tables)}\n\n"
        
        # Get all table info at once
        try:
            all_table_info = db.get_table_info()
            schema_info += f"**Database Schema:**\n"
            schema_info += f"```sql\n{all_table_info}\n```\n\n"
        except Exception as e:
            # Fallback: show table names only
            schema_info += f"**Available Tables:**\n"
            for table in tables:
                schema_info += f"- {table}\n"
            schema_info += f"\n*Note: Unable to retrieve detailed column information due to: {str(e)}*\n\n"
        
        return schema_info
    except Exception as e:
        return f"Error getting schema information: {str(e)}"


def is_schema_question(question: str) -> bool:
    """Check if the question is about database schema"""
    question_lower = question.lower()
    schema_keywords = [
        "schema", "table", "tables", "column", "columns", "structure",
        "what tables", "list tables", "show tables", "database structure",
        "table info", "table information", "describe table"
    ]
    return any(keyword in question_lower for keyword in schema_keywords)


def extract_select_sql(text: str) -> str | None:
    """Đường lùi: khi model không trả về JSON đúng khung, mò query trong text thô.

    Không còn là đường chính — xem `_ask_for_sql`.
    """
    m = re.search(r"```sql\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if candidate.lower().startswith(("select", "with")):
            return candidate.rstrip(";")
    m2 = re.search(r"```\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m2:
        block = m2.group(1).strip()
        if block.lower().startswith(("select", "with")):
            return block.rstrip(";")
    # WITH phải được thử TRƯỚC SELECT: với CTE, regex SELECT bắt từ SELECT đầu tiên
    # bên trong ngoặc, cắt mất "WITH x AS (" và trả về câu SQL thừa dấu ")".
    m4 = re.search(r"(WITH[\s\S]+)$", text, re.IGNORECASE)
    if m4:
        return m4.group(1).strip().rstrip(";")
    m3 = re.search(r"(SELECT[\s\S]+)$", text, re.IGNORECASE)
    if m3:
        return m3.group(1).strip().rstrip(";")
    return None


class SqlQuery(BaseModel):
    """Khung phản hồi duy nhất: model chỉ còn một ô để điền.

    Đây là điểm khác biệt với bản regex — text thô không còn bị 'cắt nhầm' nữa,
    và validator chặn câu không bắt đầu bằng SELECT/WITH ngay tại đây thay vì
    chờ SQL guard từ chối lúc chạy.
    """

    sql: str = Field(
        description=(
            "Exactly one read-only PostgreSQL query answering the user question. "
            "Begin with SELECT or WITH (CTEs are encouraged when they make the query clearer). "
            "Raw SQL only: no markdown fences, no explanation, no trailing semicolon. "
            "Use only tables and columns present in the schema. "
            "Do NOT add LIMIT unless the user explicitly asked for one."
        )
    )

    @field_validator("sql")
    @classmethod
    def _strip_fences_and_check(cls, value: str) -> str:
        cleaned = value.strip()
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip().rstrip(";").strip()
        if not cleaned.lower().startswith(("select", "with")):
            raise ValueError("truy vấn phải bắt đầu bằng SELECT hoặc WITH")
        return cleaned


def _ask_for_sql(llm: ChatGroq, prompt: str) -> Tuple[str | None, str, str]:
    """Gọi model một lần, trả (sql, cách_lấy_được, text_thô). Không ném exceptions.

    method='json_schema' chứ không phải 'function_calling': gpt-oss trên Groq trả
    lời bằng văn bản rồi mới gọi tool, và Groq báo lỗi
    "Tool choice is required, but model did not call a tool" với đường tool-calling.
    """
    try:
        structured = llm.with_structured_output(SqlQuery, method="json_schema", include_raw=True)
        result = structured.invoke(prompt)
    except Exception as error:
        # Model/provider không hỗ trợ structured output -> quay về text thô + regex.
        raw_msg = llm.invoke(prompt)
        text = getattr(raw_msg, "content", raw_msg)
        text = text if isinstance(text, str) else str(text)
        fallback = extract_select_sql(text)
        how = f"regex_after_schema_error({type(error).__name__})" if fallback else "schema_error"
        return fallback, how, text

    raw = result.get("raw")
    text = getattr(raw, "content", "") if raw is not None else ""
    if not isinstance(text, str):
        text = str(text)

    parsed = result.get("parsed")
    if parsed is not None:
        return parsed.sql, "json_schema", text

    fallback = extract_select_sql(text)
    if fallback:
        return fallback, "regex_fallback", text
    return None, "unparsed", text



def build_fewshot_block_from_examples(examples_path: str, question: str, top_k: int = 1, use_semantic_search: bool = True) -> Tuple[str, Dict[str, object]]:
    """
    Build few-shot examples block with optional semantic search
    
    Args:
        examples_path: Path to examples.jsonl file
        question: User question
        top_k: Number of examples to retrieve
        use_semantic_search: Whether to use ChromaDB semantic search
        
    Returns:
        Tuple of (fewshot_text, metadata)
    """
    examples_path = str(resolve_repo_path(examples_path))

    if use_semantic_search:
        try:
            from rag.rag_retriever import get_rag_retriever
            rag_agent = get_rag_retriever()
            
            # Check if collection has data
            stats = rag_agent.get_collection_stats()
            if stats.get("total_examples", 0) == 0:
                print("🔄 ChromaDB collection is empty, building index...")
                result = rag_agent.build_index_from_examples(examples_path)
                if not result["success"]:
                    print(f"❌ Failed to build index: {result['error']}")
                    return _fallback_simple_retrieval(examples_path, question, top_k)
            
            # Use semantic search
            return rag_agent.build_fewshot_prompt(question, top_k)
            
        except Exception as e:
            print(f"⚠️ Semantic search failed, falling back to simple retrieval: {str(e)}")
            return _fallback_simple_retrieval(examples_path, question, top_k)
    else:
        return _fallback_simple_retrieval(examples_path, question, top_k)


def _fallback_simple_retrieval(examples_path: str, question: str, top_k: int) -> Tuple[str, Dict[str, object]]:
    """Fallback to simple sequential retrieval"""
    selected: List[Dict[str, str]] = []
    if os.path.exists(examples_path):
        with open(examples_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if "question" in obj and "sql" in obj:
                    selected.append({"question": obj["question"], "sql": obj["sql"]})
    
    selected = selected[:top_k]
    parts = [f"Question: {ex['question']}\n```sql\n{ex['sql']}\n```" for ex in selected]
    return ("\n\n".join(parts), {
        "selected_examples": [ex["question"] for ex in selected],
        "retrieval_method": "simple_sequential"
    })


@traceable(name="sql.generate")
def generate_sql(
    question: str,
    db: SQLDatabase,
    model: str = "openai/gpt-oss-20b",
    examples_path: str = "examples.jsonl",
    top_k: int = 1,
    use_semantic_search: bool = True,
    return_debug: bool = False,
) -> Union[str, Tuple[str, Dict[str, object]]]:
    # Schema questions are now handled by Intent Agent + Orchestrator
    # No need for keyword-based detection here
    
    llm = ChatGroq(model=model, temperature=0.1)

    fewshot_text, meta = build_fewshot_block_from_examples(
        examples_path, question, top_k=top_k, use_semantic_search=use_semantic_search
    )

    # Get database schema from YAML metadata for better SQL generation
    schema_context = load_metadata_yaml()
    
    # Load prompt template from prompts/sql_prompt.txt
    template_path = resolve_repo_path("prompts/sql_prompt.txt")
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
        if fewshot_text.strip():
            template = template.replace("{fewshot}", fewshot_text)
        else:
            # "Examples:" để trống (RAG không qua threshold) làm gpt-oss lười: nó trả
            # "SELECT 1" hoặc "SELECT * FROM warehouses". Bỏ hẳn mục này còn hơn mời trống.
            template = re.sub(r"\nExamples:\s*\{fewshot\}\n", "\n", template)
        prompt = template.replace("{question}", question)
    else:
        prompt = (
            "You are a SQL assistant for a PostgreSQL database. "
            "Write exactly one read-only query, beginning with SELECT or WITH (CTEs allowed). "
            "Use accurate table/column names from the schema. Avoid destructive queries. "
            "Do NOT include LIMIT unless the user explicitly asks for it.\n" + fewshot_text + "\n"
            f"User question: {question}"
        )
    
    # Add schema context at the beginning of prompt for better visibility
    prompt = schema_context + prompt

    debug: Dict[str, object] = {"model": model, **meta, "retry": False, "prompt_snippet": prompt[:1500], "prompt_full": prompt}

    sql, how, text = _ask_for_sql(llm, prompt)
    debug["extraction"] = how
    debug["raw_response"] = text[:1500]

    if not sql:
        debug["retry"] = True
        retry_prompt = (
            schema_context + "\n"
            "Answer with one PostgreSQL-compatible query (begin with SELECT or WITH). "
            "You may use CTEs (WITH ... AS ...) if helpful. No backticks, no explanations. "
            "Do NOT include LIMIT unless explicitly requested.\n"
            f"User question: {question}"
        )
        sql, how, retry_text = _ask_for_sql(llm, retry_prompt)
        debug["retry_extraction"] = how
        debug["raw_response_retry"] = retry_text[:1500]

    if return_debug:
        return sql, debug
    return sql
