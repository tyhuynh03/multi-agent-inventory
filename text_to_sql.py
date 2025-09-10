import os
import re
import json
import pandas as pd
from typing import Tuple, Optional, List, Dict, Union
from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_groq import ChatGroq
import sqlite3

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

load_dotenv()


FEW_SHOT_EXAMPLES = [
    (
        "Get top 5 products with the lowest inventory level.",
        'SELECT "Product ID", "Product Name", "Inventory Level"\nFROM inventory\nORDER BY "Inventory Level" ASC\nLIMIT 5'
    ),
    (
        "Show total inventory quantity per category, highest first.",
        'SELECT "Category", SUM("Inventory Level") AS total_quantity\nFROM inventory\nGROUP BY "Category"\nORDER BY total_quantity DESC'
    ),
    (
        "List products where inventory is below 10 units.",
        'SELECT "Product ID", "Product Name", "Inventory Level"\nFROM inventory\nWHERE "Inventory Level" < 10\nORDER BY "Inventory Level" ASC'
    ),
    (
        "Average price by category for items with inventory > 0.",
        'SELECT "Category", AVG("Price") AS avg_price\nFROM inventory\nWHERE "Inventory Level" > 0\nGROUP BY "Category"\nORDER BY avg_price DESC'
    ),
]


class ExampleRetriever:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name)
        self.index: Optional[faiss.IndexFlatIP] = None
        self.examples: List[Dict[str, str]] = []
        self.embeddings: Optional[np.ndarray] = None

    def load_examples(self, jsonl_path: str) -> None:
        if not os.path.exists(jsonl_path):
            raise FileNotFoundError(f"Examples file not found: {jsonl_path}")
        examples: List[Dict[str, str]] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if "question" in obj and "sql" in obj:
                    examples.append({"question": obj["question"], "sql": obj["sql"]})
        if not examples:
            raise ValueError("No examples loaded from file.")
        self.examples = examples

    def build_index(self) -> None:
        questions = [ex["question"] for ex in self.examples]
        embs = self.model.encode(questions, normalize_embeddings=True)
        embs = np.asarray(embs, dtype="float32")
        dim = embs.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embs)
        self.index = index
        self.embeddings = embs

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, str]]:
        if self.index is None or self.embeddings is None or not self.examples:
            raise RuntimeError("Retriever is not ready. Call load_examples() and build_index() first.")
        q_emb = self.model.encode([query], normalize_embeddings=True)
        q_emb = np.asarray(q_emb, dtype="float32")
        scores, idxs = self.index.search(q_emb, top_k)
        idxs = idxs[0]
        results: List[Dict[str, str]] = []
        for i in idxs:
            if i == -1:
                continue
            results.append(self.examples[i])
        return results


def get_sqlalchemy_url(sqlite_path: str) -> str:
    abs_path = os.path.abspath(sqlite_path)
    return f"sqlite:///{abs_path}"


def get_db(sqlite_path: str) -> SQLDatabase:
    url = get_sqlalchemy_url(sqlite_path)
    return SQLDatabase.from_uri(url)


def extract_select_sql(text: str) -> Optional[str]:
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


def build_fewshot_block(pairs: List[Dict[str, str]]) -> str:
    blocks = []
    for ex in pairs:
        q = ex["question"]
        s = ex["sql"]
        blocks.append(f"Question: {q}\n```sql\n{s}\n```")
    return "\n\n".join(blocks)


def build_static_fewshot_block() -> str:
    blocks = []
    for q, s in FEW_SHOT_EXAMPLES:
        blocks.append(f"Question: {q}\n```sql\n{s}\n```")
        
    return "\n\n".join(blocks)


def generate_sql(
    question: str,
    db: SQLDatabase,
    model: str = "openai/gpt-oss-20b",
    use_fewshot: bool = True,
    use_retriever: bool = False,
    examples_path: str = "examples.jsonl",
    top_k: int = 4,
    return_debug: bool = False,
) -> Union[str, Tuple[str, Dict[str, object]]]:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Missing GROQ_API_KEY in environment.")

    llm = ChatGroq(model=model, temperature=0.1)
    chain = create_sql_query_chain(llm, db)

    debug: Dict[str, object] = {
        "use_fewshot": use_fewshot,
        "use_retriever": use_retriever,
        "examples_path": examples_path if use_retriever else None,
        "top_k": top_k if use_retriever else None,
        "selected_examples": [],
        "prompt_snippet": None,
        "raw_response": None,
        "model": model,
    }

    fewshot_text = ""
    if use_retriever:
        try:
            retriever = ExampleRetriever()
            retriever.load_examples(examples_path)
            retriever.build_index()
            selected = retriever.retrieve(question, top_k=top_k)
            debug["selected_examples"] = [ex["question"] for ex in selected]
            if selected:
                fewshot_text = "\n\nFollow the style and schema strictly as in these retrieved examples:\n" + build_fewshot_block(selected)
        except Exception as e:
            debug["retriever_error"] = str(e)
            if use_fewshot:
                fewshot_text = "\n\nFollow the style and schema strictly as in these examples:\n" + build_static_fewshot_block()
    else:
        if use_fewshot:
            fewshot_text = "\n\nFollow the style and schema strictly as in these examples:\n" + build_static_fewshot_block()

    prompt = (
        "You are a SQL assistant for a SQLite database. "
        "Return exactly one SELECT statement only, enclosed in a ```sql``` block, with no explanations. "
        "Use accurate table/column names from the schema. Avoid destructive queries." + fewshot_text + "\n"
        f"User question: {question}"
    )

    debug["prompt_snippet"] = prompt[:1500]

    raw = chain.invoke({"question": prompt})
    if isinstance(raw, dict):
        text = raw.get("query") or raw.get("result") or ""
    else:
        text = raw or ""
    if not isinstance(text, str):
        text = str(text)

    debug["raw_response"] = text[:1500]

    sql = extract_select_sql(text)
    if not sql:
        raise RuntimeError("Failed to extract a SELECT statement from the model response.")

    if return_debug:
        return sql, debug
    return sql


def run_sql(db: SQLDatabase, sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
    if not sql.strip().lower().startswith("select"):
        return pd.DataFrame(), "Only SELECT statements are allowed for safety."
    engine = getattr(db, "engine", None) or getattr(db, "_engine", None)
    if engine is not None:
        try:
            from pandas import read_sql_query
            with engine.connect() as conn:
                df = read_sql_query(sql, conn)
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)
    return pd.DataFrame(), "SQLDatabase engine is not available in this version; use run_sqlite(db_path, sql)."


def run_sqlite(db_path: str, sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
    if not sql.strip().lower().startswith("select"):
        return pd.DataFrame(), "Only SELECT statements are allowed for safety."
    try:
        conn = sqlite3.connect(db_path)
        try:
            df = pd.read_sql_query(sql, conn)
            return df, None
        finally:
            conn.close()
    except Exception as e:
        return pd.DataFrame(), str(e)
