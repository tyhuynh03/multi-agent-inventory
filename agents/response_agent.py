"""
Response Agent - Tạo câu trả lời ngôn ngữ tự nhiên từ kết quả truy vấn
"""

from typing import Optional
import os
import pandas as pd
from langchain_groq import ChatGroq
from utils.logger import traceable
from configs.settings import GROQ_MODEL_NAME


class ResponseAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=GROQ_MODEL_NAME,
            temperature=0.2,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )

    @traceable(name="response.generate")
    def generate_response(self, question: str, df: Optional[pd.DataFrame], sql: Optional[str] = None) -> str:
        """
        Sinh câu trả lời ngắn gọn từ câu hỏi + bảng kết quả.
        Trả về tiếng Anh để đồng bộ giao diện (có thể đổi về sau).
        """
        if df is None or df.empty:
            base = "No data was returned for this query."
            return base

        # Chuẩn hóa preview nhỏ gọn
        try:
            preview_csv = df.head(5).to_csv(index=False)
        except Exception:
            preview_csv = ""

        cols = ", ".join([str(c) for c in df.columns.tolist()])
        row_count = len(df)

        system = (
            "You are a concise analytics assistant. Given a user question and the resulting table, "
            "answer in AT MOST ONE sentence, mirroring the user's request. "
            "Be factual and precise. Do NOT add statistics like mean/min/max/quartiles unless explicitly asked. "
            "No markdown, no extra commentary."
        )

        user = f"""
Question:
{question}

SQL (for context):
{sql or "(generated)"}

Columns: {cols}
Rows: {row_count}

Preview (first 5 rows CSV):
{preview_csv}

Instructions:
- Write at most 1 sentence.
- Be precise and avoid speculation.
- If a single value is present, state it succinctly.
- No markdown fences.
"""

        try:
            msg = self.llm.invoke([{"role": "system", "content": system}, {"role": "user", "content": user}])
            content = getattr(msg, "content", "").strip()
            return content or "Summary generated."
        except Exception:
            # Fallback không LLM
            return f"Returned {row_count} rows with columns: {cols}."


