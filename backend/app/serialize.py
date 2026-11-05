from __future__ import annotations

import json
from typing import Any

from .db import jsonable
from .sql_guard import SqlForbidden


def sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def dataframe_payload(frame, max_rows: int) -> dict:
    """DataFrame -> JSON an toàn cho frontend, không nhét object Python vào response."""
    if frame is None:
        return None

    total = int(len(frame))
    shown = frame.head(max_rows)
    return {
        "columns": [str(column) for column in shown.columns],
        "rows": [[jsonable(cell) for cell in row] for row in shown.itertuples(index=False, name=None)],
        "row_count": total,
        "returned_rows": int(len(shown)),
        "truncated": total > max_rows,
    }


def figure_payload(figure) -> dict | None:
    """Plotly figure -> spec thuần JSON để plotly.js render. matplotlib trả về None."""
    if figure is None:
        return None
    to_json = getattr(figure, "to_plotly_json", None)
    if not callable(to_json):
        return None
    try:
        return to_json()
    except Exception:
        return None


def error_payload(error: Exception) -> dict:
    if isinstance(error, SqlForbidden):
        return {"type": "sql_forbidden", "message": error.reason}
    return {"type": type(error).__name__, "message": str(error).splitlines()[0][:400]}
