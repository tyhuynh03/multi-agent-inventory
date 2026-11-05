import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent

# agents/ và rag/ vẫn print emoji trực tiếp ra stdout; console Windows mặc định là
# cp1252 nên UnicodeEncodeError giết cả pipeline. errors="replace" chỉ ảnh hưởng log.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# agents/, rag/, db/, configs/ sống ở thư mục gốc repo, không phải trong backend/
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _db_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    user = os.getenv("DB_USER", "inventory_user")
    password = os.getenv("DB_PASSWORD", "inventory_pass")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "inventory_db")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


class Settings:
    db_url: str = _db_url()
    max_rows: int = _int_env("INV_API_MAX_ROWS", 500)
    statement_timeout_ms: int = _int_env("INV_API_STATEMENT_TIMEOUT_MS", 10_000)
    pool_size: int = _int_env("INV_API_POOL_SIZE", 5)
    model: str = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b")
    examples_path: str = str(ROOT_DIR / "data" / "examples.jsonl")
    rag_top_k: int = _int_env("INV_RAG_TOP_K", 2)
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "INV_API_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]


settings = Settings()
