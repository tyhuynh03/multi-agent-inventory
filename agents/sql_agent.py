import os
from typing import Dict, List, Tuple, Union

from langchain.chains import create_sql_query_chain
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase

from utils.logger import traceable

import json
import re
from pathlib import Path


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
    m = re.search(r"```sql\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if candidate.lower().startswith("select"):
            return candidate.rstrip(";")
    m2 = re.search(r"```\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m2:
        block = m2.group(1).strip()
        if block.lower().startswith("select"):
            return block.rstrip(";")
    m3 = re.search(r"(SELECT[\s\S]+)$", text, re.IGNORECASE)
    if m3:
        return m3.group(1).strip().rstrip(";")
    return None


def build_fewshot_block_from_examples(examples_path: str, question: str, top_k: int = 4) -> Tuple[str, Dict[str, object]]:
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
    return ("\n\n".join(parts), {"selected_examples": [ex["question"] for ex in selected]})


@traceable(name="sql.generate")
def generate_sql(
    question: str,
    db: SQLDatabase,
    model: str = "openai/gpt-oss-20b",
    examples_path: str = "examples.jsonl",
    top_k: int = 4,
    return_debug: bool = False,
) -> Union[str, Tuple[str, Dict[str, object]]]:
    # Check if this is a schema question
    if is_schema_question(question):
        schema_info = get_schema_info(db)
        if return_debug:
            return schema_info, {"type": "schema", "question": question}
        return schema_info
    
    llm = ChatGroq(model=model, temperature=0.1)
    chain = create_sql_query_chain(llm, db)

    fewshot_text, meta = build_fewshot_block_from_examples(examples_path, question, top_k=top_k)

    # Load prompt template from prompts/sql_prompt.txt
    template_path = Path("prompts/sql_prompt.txt")
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
        prompt = template.replace("{fewshot}", fewshot_text).replace("{question}", question)
    else:
        prompt = (
            "You are a SQL assistant for a SQLite database. "
            "Return exactly one SELECT statement only, enclosed in a ```sql``` block, with no explanations. "
            "Use accurate table/column names from the schema. Avoid destructive queries. "
            "Do NOT include LIMIT unless the user explicitly asks for it.\n" + fewshot_text + "\n" 
            f"User question: {question}"
        )

    debug: Dict[str, object] = {"model": model, **meta, "retry": False, "prompt_snippet": prompt[:1500]}

    raw = chain.invoke({"question": prompt})
    text = raw if isinstance(raw, str) else str(raw)
    debug["raw_response"] = text[:1500]

    sql = extract_select_sql(text)
    if not sql:
        debug["retry"] = True
        retry_prompt = (
            "Output ONLY one SQLite-compatible SELECT statement. No backticks, no explanations. "
            "Do NOT include LIMIT unless explicitly requested.\n"
            f"User question: {question}"
        )
        retry_text_msg = llm.invoke(retry_prompt)
        retry_text = getattr(retry_text_msg, "content", retry_text_msg)
        if not isinstance(retry_text, str):
            retry_text = str(retry_text)
        if retry_text.strip().lower().startswith("select"):
            sql = retry_text.strip().rstrip(";")
        else:
            sql = extract_select_sql(retry_text)

    if return_debug:
        return sql, debug
    return sql
