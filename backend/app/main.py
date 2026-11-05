"""API HTTP/WebSocket thay cho giao diện Streamlit.

Luồng chat: agents/ + rag/ dùng lại nguyên bản, chỉ thêm hook on_event để phát tiến độ.
Luồng SQL console và schema: đi qua sql_guard + transaction read-only của riêng backend.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import settings
from .db import db_status, read_schema, run_readonly
from .pipeline import stream_question
from .sql_guard import SqlForbidden

app = FastAPI(
    title="Multi-Agent Inventory API",
    version="0.1.0",
    description="Text-to-SQL + RAG + analytics cho dữ liệu kho hàng, phục vụ frontend tách biệt.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=600)
    use_rag: bool = True


class SqlRequest(BaseModel):
    sql: str = Field(min_length=2, max_length=4000)
    max_rows: int | None = Field(default=None, ge=1, le=2000)


@app.get("/")
def index() -> dict:
    return {
        "name": "Multi-Agent Inventory API",
        "docs": "/docs",
        "endpoints": ["/api/health", "/api/schema", "/api/sql", "/api/chat/stream"],
    }


@app.get("/api/health")
def health() -> dict:
    database = db_status()
    return {
        "status": "ok" if database.get("ok") else "degraded",
        "db": database,
        "model": settings.model,
        "limits": {
            "max_rows": settings.max_rows,
            "statement_timeout_ms": settings.statement_timeout_ms,
        },
        "ai_pipeline": {
            "groq_api_key_configured": bool(os.getenv("GROQ_API_KEY")),
            "examples_path": settings.examples_path,
            "rag_top_k": settings.rag_top_k,
        },
    }


@app.get("/api/schema")
def schema() -> list[dict]:
    try:
        return read_schema()
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error).splitlines()[0]) from error


@app.post("/api/sql")
def sql_console(request: SqlRequest) -> dict:
    try:
        return run_readonly(request.sql, request.max_rows)
    except SqlForbidden as forbidden:
        raise HTTPException(status_code=400, detail=forbidden.reason) from forbidden
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error).splitlines()[0]) from error


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_question(request.question, request.use_rag),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
