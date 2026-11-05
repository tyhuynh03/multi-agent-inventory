from __future__ import annotations

import datetime as dt
import decimal
import time
from typing import Any

from sqlalchemy import create_engine

from .config import settings
from .sql_guard import validate_read_only

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.db_url,
            pool_size=settings.pool_size,
            max_overflow=settings.pool_size,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return _engine


def jsonable(value: Any) -> Any:
    """Ép giá trị DB sang kiểu JSON hợp lệ (NaN/Infinity -> null để JSON.parse không sập)."""
    if value is None:
        return None
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, "item"):
        try:
            return jsonable(value.item())
        except Exception:
            pass
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "replace")
    return str(value)


def run_readonly(sql: str, max_rows: int | None = None) -> dict:
    """Chạy câu truy vấn chỉ-đọc trong transaction có timeout và giới hạn dòng."""
    guarded = validate_read_only(sql)
    limit = settings.max_rows if max_rows is None else min(int(max_rows), settings.max_rows)
    timeout_ms = int(settings.statement_timeout_ms)

    started = time.perf_counter()
    with get_engine().connect() as conn:
        try:
            # SET LOCAL không nhận bind param, timeout_ms đã được ép int ở trên.
            conn.exec_driver_sql(f"SET LOCAL statement_timeout = {timeout_ms}")
            conn.exec_driver_sql("SET LOCAL TRANSACTION READ ONLY")
            cursor = conn.exec_driver_sql(guarded)
            columns = list(cursor.keys()) if cursor.returns_rows else []
            fetched = cursor.fetchmany(limit + 1) if cursor.returns_rows else []
        finally:
            conn.rollback()

    truncated = len(fetched) > limit
    return {
        "sql": guarded,
        "columns": [str(column) for column in columns],
        "rows": [[jsonable(cell) for cell in row] for row in fetched[:limit]],
        # fetchmany không biết tổng số dòng thật, chỉ biết là còn nhiều hơn giới hạn.
        "row_count": None if truncated else len(fetched),
        "returned_rows": min(len(fetched), limit),
        "truncated": truncated,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def db_status() -> dict:
    try:
        started = time.perf_counter()
        with get_engine().connect() as conn:
            conn.exec_driver_sql("SET LOCAL statement_timeout = 3000")
            conn.exec_driver_sql("SET LOCAL TRANSACTION READ ONLY")
            tables = [
                row[0]
                for row in conn.exec_driver_sql(
                    "SELECT table_name FROM information_schema.tables"
                    " WHERE table_schema = 'public' ORDER BY table_name"
                )
            ]
            conn.rollback()
        return {
            "ok": True,
            "tables": tables,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    except Exception as error:
        return {"ok": False, "error": str(error).splitlines()[0]}


def read_schema() -> list[dict]:
    """Cột + kiểu của từng bảng, đủ để frontend hiển thị schema và viết prompt."""
    with get_engine().connect() as conn:
        try:
            conn.exec_driver_sql("SET LOCAL statement_timeout = 5000")
            conn.exec_driver_sql("SET LOCAL TRANSACTION READ ONLY")
            rows = conn.exec_driver_sql(
                "SELECT table_name, ordinal_position, column_name, data_type, is_nullable"
                " FROM information_schema.columns WHERE table_schema = 'public'"
                " ORDER BY table_name, ordinal_position"
            ).fetchall()
        finally:
            conn.rollback()

    by_table: dict[str, dict] = {}
    for table_name, _position, column_name, data_type, nullable in rows:
        table = by_table.setdefault(table_name, {"table": table_name, "columns": []})
        table["columns"].append(
            {
                "name": str(column_name),
                "type": str(data_type),
                "nullable": nullable == "YES",
            }
        )
    return list(by_table.values())
