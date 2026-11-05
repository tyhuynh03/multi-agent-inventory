from __future__ import annotations

import queue
import threading
import time
from collections.abc import Iterator

from .config import settings
from .serialize import dataframe_payload, error_payload, figure_payload, sse

_orchestrator = None
_orchestrator_lock = threading.Lock()


def get_orchestrator():
    """Import chậm: agents/ kéo theo langchain + chromadb + torch, không cần cho /api/sql."""
    global _orchestrator
    with _orchestrator_lock:
        if _orchestrator is None:
            import agents.orchestrator as orchestrator_module
            from agents.orchestrator import OrchestratorAgent

            orchestrator_module.run_sql_unified = guarded_sql_runner
            _orchestrator = OrchestratorAgent(db_type="postgresql")
        return _orchestrator


def guarded_sql_runner(sql: str, db_type: str = "postgresql") -> tuple:
    """Thế chỗ run_sql_unified: SQL do LLM sinh ra cũng phải qua guard + timeout + row cap.

    Bản gốc trong db/connection.py chỉ kiểm tra token đầu rồi pd.read_sql_query,
    tức là không có statement_timeout và một SELECT chậm sẽ treo cả worker.
    """
    import pandas as pd

    from .db import run_readonly

    try:
        payload = run_readonly(sql)
    except Exception as error:
        return pd.DataFrame(), f"{type(error).__name__}: {error}"
    return pd.DataFrame(payload["rows"], columns=payload["columns"]), None


def _result_events(result: dict) -> Iterator[tuple[str, dict]]:
    intent = result.get("intent")
    agent = result.get("agent")

    if not result.get("success"):
        yield "error", {
            "message": result.get("error") or "Pipeline trả về kết quả không hợp lệ",
            "intent": intent,
            "agent": agent,
            "sql": result.get("sql"),
        }

    if result.get("schema_info"):
        yield "schema", {"markdown": result["schema_info"]}

    if result.get("data") is not None:
        yield "table", dataframe_payload(result["data"], settings.max_rows)

    chart = figure_payload(result.get("chart"))
    if chart is not None:
        yield "chart", {"spec": chart, "viz_spec": result.get("viz_spec")}

    steps = (result.get("debug") or {}).get("steps") or []
    if steps:
        yield "timings", {"steps": steps}

    yield "answer", {
        "text": result.get("response"),
        "table_md": result.get("response_table_md"),
        "message": result.get("message"),
        "intent": intent,
        "agent": agent,
        "analytics_type": result.get("analytics_type"),
        "success": bool(result.get("success")),
    }


def stream_question(question: str, use_rag: bool = True) -> Iterator[str]:
    """Chạy pipeline trong thread riêng, đẩy từng bước ra SSE ngay khi có."""
    started = time.perf_counter()
    yield sse("start", {"question": question, "use_rag": use_rag, "model": settings.model})

    events: queue.Queue = queue.Queue()

    def worker() -> None:
        try:
            orchestrator = get_orchestrator()
            result = orchestrator.run_agent(
                user_question=question,
                db_type="postgresql",
                use_retriever=use_rag,
                examples_path=settings.examples_path,
                top_k=settings.rag_top_k,
                on_event=lambda name, data: events.put((name, data)),
            )
            events.put(("__result__", result))
        except ModuleNotFoundError as missing:
            events.put(("__error__", missing))
        except Exception as error:
            events.put(("__error__", error))

    threading.Thread(target=worker, daemon=True).start()

    while True:
        try:
            name, payload = events.get(timeout=10)
        except queue.Empty:
            yield ": keep-alive\n\n"
            continue

        if name == "__result__":
            for event_name, data in _result_events(payload):
                yield sse(event_name, data)
            break

        if name == "__error__":
            if isinstance(payload, ModuleNotFoundError):
                yield sse(
                    "error",
                    {
                        "type": "missing_dependencies",
                        "message": (
                            f"Thiếu module {payload.name}. Chạy: pip install -r requirements.txt "
                            "ở thư mục gốc repo (bộ AI deps) rồi khởi động lại backend."
                        ),
                    },
                )
            else:
                yield sse("error", error_payload(payload))
            break

        yield sse(name, payload)

    yield sse("done", {"elapsed_ms": round((time.perf_counter() - started) * 1000, 1)})
