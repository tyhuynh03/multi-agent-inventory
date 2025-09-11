import os

# Defaults (can be overridden by environment variables)
DEFAULT_DB_PATH = os.getenv("INV_DB_PATH", "data/inventory.db")
DEFAULT_MODEL = os.getenv("INV_MODEL", "openai/gpt-oss-20b")
DEFAULT_EXAMPLES_PATH = os.getenv("INV_EXAMPLES_PATH", "data/examples.jsonl")

# RAG / Retrieval
RAG_TOP_K = int(os.getenv("INV_RAG_TOP_K", "2"))

# Safety/Policy
SELECT_ONLY = True
