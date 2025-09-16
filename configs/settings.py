import os

# Defaults (can be overridden by environment variables)
DEFAULT_DB_PATH = os.getenv("INV_DB_PATH", "data/inventory.db")
DEFAULT_MODEL = os.getenv("INV_MODEL", "openai/gpt-oss-20b")
DEFAULT_EXAMPLES_PATH = os.getenv("INV_EXAMPLES_PATH", "data/examples.jsonl")

# Groq model name
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b")

# RAG / Retrieval
RAG_TOP_K = int(os.getenv("INV_RAG_TOP_K", "2"))
USE_SEMANTIC_SEARCH = os.getenv("INV_USE_SEMANTIC_SEARCH", "true").lower() == "true"
RAG_SIMILARITY_THRESHOLD = float(os.getenv("INV_RAG_SIMILARITY_THRESHOLD", "0.3"))
RAG_EMBEDDING_MODEL = os.getenv("INV_RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = os.getenv("INV_CHROMA_PERSIST_DIR", "data/chroma_db")

# Safety/Policy
SELECT_ONLY = True
