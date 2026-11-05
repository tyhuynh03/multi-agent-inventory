"""Rào chắn read-only cho SQL đến từ người dùng hoặc từ LLM.

Thay cho SELECT_ONLY trong configs/settings.py — hằng số đó chưa từng được import
ở bất kỳ đâu nên chưa bao giờ có tác dụng.
"""

import re

_COMMENT_LINE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.S)
_SINGLE_QUOTED = re.compile(r"'(?:[^']|'')*'")
_DOUBLE_QUOTED = re.compile(r'"(?:[^"]|"")*"')

_ALLOWED_STARTS = ("select", "with", "explain")

_FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "COPY", "VACUUM", "ANALYZE", "REINDEX", "CLUSTER",
    "REFRESH", "LISTEN", "NOTIFY", "CALL", "DO", "MERGE", "PREPARE",
    "DEALLOCATE", "DISCARD", "LOCK", "COMMENT", "EXECUTE", "BEGIN", "COMMIT",
    "ROLLBACK", "SAVEPOINT", "INTO", "TABLESAMPLE SYSTEM",
)

_FORBIDDEN_PATTERNS = (
    r"\bpg_read_file\b",
    r"\bpg_ls_dir\b",
    r"\bpg_stat\b",
    r"\bpg_authid\b",
    r"\bpg_shadow\b",
    r"\bpg_sleep\b",
    r"\bpg_terminate_backend\b",
    r"\bpg_cancel_backend\b",
    r"\bdblink\w*\b",
    r"\blo_import\b",
    r"\blo_export\b",
    r"\bcopy\s+to\s+program\b",
    r"\bxpath_array\b",
)

_FORBIDDEN_RE = re.compile(
    "|".join(r"\b" + kw.replace(" ", r"\s+") + r"\b" for kw in _FORBIDDEN_KEYWORDS),
    re.I,
)
_DANGEROUS_RE = re.compile("|".join(_FORBIDDEN_PATTERNS), re.I)


class SqlForbidden(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _strip_noise(sql: str) -> str:
    without_comments = _COMMENT_BLOCK.sub(" ", _COMMENT_LINE.sub(" ", sql))
    # Bỏ nội dung chuỗi để 'Drop Table' trong literal không chặn câu hỏi hợp lệ,
    # nhưng vẫn giữ dấu nháy đơn lồng nhau.
    without_strings = _SINGLE_QUOTED.sub("''", without_comments)
    return _DOUBLE_QUOTED.sub('""', without_strings)


def validate_read_only(sql: str) -> str:
    """Kiểm tra an toàn rồi trả về CHÍNH câu SQL được gửi vào (chỉ cắt khoảng trắng và `;` cuối).

    Bản mask chuỗi chỉ dùng để xét luật — nếu trả nó ra thì mọi literal như
    '2024-01-01' bị thay bằng '' và query chạy sai mà không báo lỗi.
    """
    if not sql or not sql.strip():
        raise SqlForbidden("Câu truy vấn rỗng")

    cleaned = _strip_noise(sql).strip().rstrip(";").strip()
    if not cleaned:
        raise SqlForbidden("Câu truy vấn chỉ chứa comment")

    if ";" in cleaned:
        raise SqlForbidden("Không cho phép nhiều câu truy vấn trong một lần gửi")

    first_word = cleaned.split(None, 1)[0].lower()
    if not first_word.startswith(_ALLOWED_STARTS):
        raise SqlForbidden(f"Chỉ cho phép SELECT/WITH/EXPLAIN, nhận được '{first_word}'")

    blocked = _FORBIDDEN_RE.search(cleaned)
    if blocked:
        raise SqlForbidden(f"Khoá bị chặn trong câu truy vấn: {blocked.group(0).upper()}")

    dangerous = _DANGEROUS_RE.search(cleaned)
    if dangerous:
        raise SqlForbidden(f"Hàm tiếp cận hệ thống bị chặn: {dangerous.group(0)}")

    guarded = sql.strip()
    while guarded.endswith(";"):
        guarded = guarded[:-1].rstrip()
    return guarded
