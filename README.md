# 🤖 Multi-Agent for Inventory (SQLite + LangChain, Groq)

Text-to-SQL + Visualization với kiến trúc agent gọn nhẹ. Hỗ trợ RAG few-shot, auto chart, và LangSmith tracing.

## Features
- Groq LLM (mặc định `openai/gpt-oss-20b`).
- RAG few-shot từ `data/examples.jsonl` (top-k cấu hình được).
- Agent điều phối: query thường hoặc visualize (tự vẽ chart theo dữ liệu).
- Tracing (LangSmith) cho từng bước: intent → sql.generate → sql.exec → viz.render.

## Project layout (rút gọn)
```
agents/
  sql_agent.py        # sinh SQL từ câu hỏi (đọc prompts/sql_prompt.txt)
  viz_agent.py        # suy luận & render chart (matplotlib)
db/
  connection.py       # kết nối và thực thi SQLite an toàn
configs/
  settings.py         # DEFAULT_DB_PATH, DEFAULT_MODEL, RAG_TOP_K ...
prompts/
  sql_prompt.txt      # template prompt cho SQL agent
data/
  retail_store_inventory.csv
  inventory.db
  examples.jsonl
app.py                # UI Streamlit (orchestrator nhẹ)
```

## Setup
1) Tạo venv và cài thư viện
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
2) Chuẩn bị dữ liệu (csv → SQLite)
```bash
mkdir data 2>$null
python load_csv_to_sqlite.py data/retail_store_inventory.csv --db data/inventory.db --table inventory
```
3) Cấu hình API key
Tạo `.env` ở thư mục dự án:
```
GROQ_API_KEY=your_groq_api_key_here
```
4) Chạy ứng dụng
```bash
streamlit run app.py
```

## Sử dụng nhanh
- Nhập câu hỏi ở tab "Text-to-SQL".
- (Tùy chọn) Bật “Use retrieved few-shot (RAG)” và chỉnh `Top-k`.
- Bật “Auto visualize” để tự vẽ (ưu tiên line theo thời gian, fallback bar).

Ví dụ câu hỏi:
- Query: `How many units of product P0001 were sold at store S001 on 2022-01-01?`
- Visualize: `Trend of total inventory for store S001 from 2022-01-01 to 2022-03-31.`

## Cấu hình qua ENV (configs/settings.py)
- `INV_DB_PATH` (mặc định `data/inventory.db`)
- `INV_MODEL` (mặc định `openai/gpt-oss-20b`)
- `INV_EXAMPLES_PATH` (mặc định `data/examples.jsonl`)
- `INV_RAG_TOP_K` (mặc định `2`)

## Tracing (tùy chọn)
Thêm vào `.env` nếu dùng LangSmith:
```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsm_...
LANGSMITH_PROJECT=inventory-text-to-sql
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## Ghi chú an toàn
- Chỉ cho phép `SELECT` để tránh thao tác phá hủy dữ liệu.
- Các cột có dấu cách cần đặt trong dấu ngoặc kép (ví dụ: "Product ID").

## Roadmap ngắn
- Validator + auto‑repair tên bảng/cột.
- Intent Classifier (LLM) & skill registry cho các pipeline (low stock report…).
- Test smoke (pytest) và Dockerfile.
