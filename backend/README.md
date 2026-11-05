# Backend API (FastAPI) + Frontend (React)

Thay thế giao diện Streamlit bằng một API JSON/SSE và một SPA React. Pipeline AI cũ
(`agents/orchestrator.py`) được dùng lại qua event hook, còn `app.py` giữ nguyên để
đối chiếu — cả hai đường đều chạy song song.

```
multi-agent-inventory/
├── app.py                  Streamlit bản gốc (không sửa)
├── agents/                 pipeline multi-agent (dùng lại, thêm on_event hook)
├── backend/                FastAPI app này
│   ├── app/config.py       đọc .env ở gốc repo + backend/.env
│   ├── app/main.py         endpoints
│   ├── app/sql_guard.py    chặn SQL không đọc
│   ├── app/db.py           connection pool + chạy truy vấn có giới hạn
│   ├── app/pipeline.py     cầu nối orchestrator (sync) -> SSE
│   ├── sql/readonly_role.sql
│   └── requirements.txt
└── web/                    React 19 + Vite 8 + TypeScript
```

## Chạy

Cần PostgreSQL đang chạy (container `inventory_postgres` hoặc `docker-start.bat`).

```bash
# 1. Backend
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Frontend (terminal khác)
cd web
npm install
npm run dev                        # http://localhost:5173
```

Vite proxy `/api` -> `http://localhost:8000`, nên frontend không cần cấu hình CORS
khi chạy local.

## Endpoints

| Method | Đường dẫn            | Nội dung |
|--------|----------------------|----------|
| GET    | `/api/health`        | DB status, danh sách bảng, model, giới hạn, trạng thái `GROQ_API_KEY` |
| GET    | `/api/schema`        | Bảng + cột + kiểu dữ liệu, đọc trực tiếp từ `information_schema` |
| POST   | `/api/sql`           | Chạy một câu SELECT, trả `{columns, rows, row_count, truncated, elapsed_ms}` |
| POST   | `/api/chat/stream`   | SSE: agent trả lời từng bước |

### SSE events

`start` → `intent` / `sql` / `executing` / `chart_planning` / `analytics` →
`schema` → `table` → `chart` → `timings` → `answer`, luôn kết thúc bằng `done`.
Lỗi gửi bằng event `error` (frontend hiển thị trong timeline, không abort stream).

## Cấu hình (env)

| Biến | Mặc định | Ý nghĩa |
|------|----------|----------|
| `DATABASE_URL` | tự ghép từ `DB_*` | Ghi đè toàn bộ connection string |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | `inventory_user` / `inventory_pass` / `localhost` / `5432` / `inventory_db` | |
| `INV_API_MAX_ROWS` | `500` | Cắt số dòng trả về |
| `INV_API_STATEMENT_TIMEOUT_MS` | `10000` | `statement_timeout` cho mỗi truy vấn |
| `INV_API_POOL_SIZE` | `5` | Size của connection pool |
| `INV_API_CORS_ORIGINS` | `http://localhost:5173` | Chỉ cần khi frontend không dùng proxy |
| `GROQ_API_KEY` | (trống) | Bắt buộc cho `/api/chat/stream` |
| `GROQ_MODEL_NAME` | `openai/gpt-oss-20b` | |

## Lớp bảo vệ SQL

`/api/sql` nhận SQL do người dùng gõ, `/api/chat/stream` nhận SQL do LLM sinh ra.
Đường đầu gọi thẳng `db.run_readonly()`. Đường thứ hai đi qua `agents/orchestrator.py`
(mã cũ, gọi `db.connection.run_sql_unified`), nên `pipeline.guarded_sql_runner` thay
chỗ hàm đó bằng bản có guard — nếu không, SQL của LLM chạy mà không có timeout,
không giới hạn dòng và không READ ONLY.

Ba lớp trong `db.run_readonly()`:

1. `sql_guard.validate_read_only()` — bỏ comment/chuỗi, từ chối nhiều câu (`;`), chỉ
   cho mở đầu bằng `SELECT`/`WITH`/`EXPLAIN`, chặn keyword ghi và hàm nguy hiểm (`pg_sleep`, `pg_read_file`, ...).
2. Transaction `READ ONLY` + `statement_timeout` — chặn ghi kể cả khi guard bị vượt.
3. `fetchmany(max_rows + 1)` — giới hạn số dòng; khi bị cắt thì `row_count = null`
   (không dám đoán tổng).

Guard chỉ là lớp mềm. Lớp cứng thật là role chỉ đọc:

```bash
# chạy 1 lần, sau đó đặt DB_USER=inventory_ro trong .env
docker exec -i inventory_postgres psql -U postgres < backend/sql/readonly_role.sql
```

## Ba bẫy đã gặp

* `agents/*.py` và `rag/*.py` vẫn `print()` emoji ra stdout; console Windows mặc định
  là cp1252 nên pipeline chết giữa chừng bằng `UnicodeEncodeError`. `config.py` reconfigure
  stdout/stderr sang UTF-8 cho toàn backend.
* SQLAlchemy 2.1 hiểu `postgresql://` là psycopg3, trong khi repo chỉ pin
  `psycopg2-binary` -> `No module named 'psycopg'`. `db/connection.py` giờ sinh
  `postgresql+psycopg2://` (áp dụng cho cả `app.py`).
* **Đường dẫn tương đối + CWD.** uvicorn chạy từ `backend/`, còn `load_metadata_yaml()`,
  `prompts/sql_prompt.txt` và `CHROMA_PERSIST_DIR` lại mở theo đường dẫn tương đối.
  Hậu quả là im lặng (không exception): schema context rơi về chuỗi fallback 32 ký tự
  (`**Available Tables:** inventory`) nên model bịa cột `customer_id`, `month`,
  `product_name`; còn ChromaDB thì tự tạo một bản sao `backend/data/chroma_db` — chạy
  được nhưng là index nhân bản vô nghĩa và rất dễ gây nhầm khi debug.
  Chữa: `resolve_repo_path()` trong `agents/sql_agent.py` và `repo_path()` trong
  `configs/settings.py` — mọi đường dẫn neo vào repo root bất kể CWD.

## Sinh SQL: structured output thay cho regex

`generate_sql` gọi `llm.with_structured_output(SqlQuery, method="json_schema", include_raw=True)`
(`/api/sql` không đổi). `SqlQuery` chỉ có một trường `sql`, validator tự cắt fence/ngoặc đơn
và **từ chối** câu không bắt đầu bằng `SELECT`/`WITH` ngay tại tầng parse.

* `method="function_calling"` không dùng được với `openai/gpt-oss-20b` trên Groq: model
  viết văn bản trước rồi mới gọi tool, Groq trả 400
  `Tool choice is required, but model did not call a tool`. `json_schema` chạy ổn.
* `include_raw=True` để không nổ: nếu parse fail, `extract_select_sql()` (regex cũ) vẫn
  mò SQL từ text thô, và `debug["extraction"]` ghi rõ đi đường nào
  (`json_schema` / `regex_fallback` / `regex_after_schema_error(...)`).
* `fewshot` rỗng thì bỏ hẳn mục `Examples:` khỏi prompt — để một header không nội dung
  khiến gpt-oss trả `SELECT 1`.

## Đã kiểm chứng / chưa kiểm chứng

Đã kiểm chứng với Groq key thật, model `openai/gpt-oss-20b`, dữ liệu thật (33.919 dòng sales):

| Câu hỏi | Intent | Kết quả |
|---------|--------|---------|
| "How many warehouses are there?" | query | `SELECT COUNT(*)...` -> "There are 4 warehouses." |
| "Show sales by customer type as a bar chart" | visualize | bar chart Plotly, 3 dòng, render SVG trong UI |
| "Which products will run out of stock soon?" | inventory_analytics | bảng cover-days + nhận xét |

Battery tiếng Việt sau khi chuyển sang structured output — 5/5 chạy được qua SSE, CTE và
window function còn nguyên (chính là họ lỗi mà regex cắt mất `WITH ... AS (`).
Kiểm chứng tách `generate_sql`: 4/4 câu lấy được SQL bằng `json_schema`, không câu nào phải
dùng regex fallback; số liệu đã đối chiếu lại bằng truy vấn trực tiếp:

| Câu hỏi | SQL sinh ra | Kết quả |
|---------|-------------|---------|
| "Kho nào có tổng giá trị tồn kho lớn nhất?" | CTE + `RANK() OVER` | GUT930 / Martensville — 16.858.273,68 ✅ |
| "Top 3 khách hàng Wholesale có doanh thu cao nhất ở mỗi tỉnh" | CTE + `ROW_NUMBER() PARTITION BY` | Quebec: SO-041062 2.552.551 ✅ |
| "Tháng nào trong năm 2023 có doanh thu cao nhất?" | CTE + `DATE_TRUNC('month')` | Tháng 6 — 6.120.299 ✅ |
| "Sản phẩm nào có số lần bán nhiều nhất tại kho GUT930?" | CTE tự join `skus` | Product 266 — 93 lần ✅ |
| "Tỷ lệ khách hàng Wholesale so với Retail là bao nhiêu?" | `CASE ... NULLIF(...,0)` | `NULL` — dữ liệu chỉ có Wholesale/Distributor/Export, không có Retail. Agent báo đúng "không có dữ liệu". |

Còn lại:

* `answer.text` là markdown thô (`**...**`) nhưng frontend render như text thường —
  cần một markdown renderer nhỏ nếu muốn đẹp.
* Câu hỏi đầu tiên sau khi khởi động chậm hơn nhiều (~60s) vì `sentence-transformers`
  tải model `all-MiniLM-L6-v2` (~90MB) về cache; các câu sau chỉ ~2-5s.
* Schema không có khái niệm "khách hàng" (chỉ có `customer_type` và `order_number`), nên
  câu hỏi về khách hàng agent phải thay bằng `order_number`. Đây là chỗ semantic layer
  lên tiếng.
* Chưa có test tự động cho guard/pipeline.
