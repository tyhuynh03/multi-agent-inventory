# 🤖 Multi-Agent Inventory Management System

Hệ thống quản lý kho hàng thông minh sử dụng Multi-Agent AI với PostgreSQL, LangChain và Groq.

## ⚡ Quick Start (3 bước)

```bash
# 1. Tạo file .env và điền GROQ_API_KEY
copy example.env .env

# 2. Chạy Docker
docker-start.bat

# 3. Mở trình duyệt
http://localhost:8501
```

**💡 Lấy GROQ_API_KEY miễn phí:** https://console.groq.com/keys

---

## 🚀 Tính năng chính

- **🧠 Multi-Agent AI**: Intent Classification, SQL Generation, Query Execution, Response Generation
- **🗄️ PostgreSQL Database**: Lưu trữ dữ liệu kho hàng với 4 bảng chính
- **💬 Natural Language Interface**: Hỏi đáp bằng tiếng Anh tự nhiên
- **📊 Data Visualization**: Biểu đồ và báo cáo tự động
- **🔍 Semantic Search**: Tìm kiếm thông minh với RAG (Retrieval-Augmented Generation)
- **🖥️ Streamlit Web Interface**: Giao diện web thân thiện

## 📊 Cấu trúc dữ liệu

### Bảng warehouses
- `warehouse_code`: Mã kho hàng
- `city`, `province`, `country`: Địa chỉ
- `latitude`, `longitude`: Tọa độ địa lý

### Bảng skus
- `sku_id`: Mã sản phẩm
- `sku_name`: Tên sản phẩm

### Bảng inventory
- `sku_id`, `warehouse_id`: Liên kết với bảng khác
- `vendor_name`: Nhà cung cấp
- `current_inventory_quantity`: Số lượng tồn kho
- `cost_per_sku`, `unit_price`: Giá thành và giá bán
- `total_value`: Tổng giá trị
- `average_lead_time_days`: Thời gian giao hàng trung bình

### Bảng sales
- `order_number`: Số đơn hàng
- `order_date`: Ngày đặt hàng
- `sku_id`, `warehouse_id`: Liên kết
- `customer_type`: Loại khách hàng (Export, Wholesale, Distributor)
- `order_quantity`: Số lượng đặt
- `unit_sale_price`, `revenue`: Giá bán và doanh thu

## 🚀 Chạy dự án (Khuyến nghị cho nhóm)

### ⚡ Cách 1: Chạy bằng Docker (ĐƠN GIẢN NHẤT - KHUYẾN NGHỊ)

**Yêu cầu:** Đã cài Docker Desktop

#### Bước 1: Tạo file .env
```bash
copy example.env .env
```
Mở file `.env` và điền `GROQ_API_KEY` (lấy miễn phí tại https://console.groq.com/keys)

#### Bước 2: Chạy
```bash
docker-start.bat
```
HOẶC
```bash
docker-compose up -d
```

#### Bước 3: Truy cập
```
http://localhost:8501
```

**✨ Lợi ích:**
- ✅ Không cần cài Python packages
- ✅ PostgreSQL tự động chạy
- ✅ Dữ liệu tự động load từ CSV
- ✅ RAG system tự động khởi tạo
- ✅ Mọi thứ đã setup sẵn

**📝 Lưu ý:** Lần đầu chạy mất ~2-3 phút để load dữ liệu và khởi tạo RAG.

**🛠️ Các lệnh hữu ích:**
```bash
docker-compose logs -f        # Xem logs
docker-compose down           # Dừng hệ thống
docker-compose restart        # Restart
docker-rebuild.bat            # Rebuild sau khi sửa code
```

---

### 🐍 Cách 2: Chạy trực tiếp bằng Python (CHO DEVELOPMENT)

#### 1. Clone repository
```bash
git clone <repository-url>
cd "Multi-agent system inventory"
```

#### 2. Tạo virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

#### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

#### 4. Thiết lập Environment Variables
```bash
copy example.env .env
# Mở .env và điền GROQ_API_KEY
```

**📋 Cấu hình bắt buộc:**
- `GROQ_API_KEY`: Lấy từ [Groq Console](https://console.groq.com/keys) (FREE)

**🔧 Cấu hình tùy chọn:**
- `LANGSMITH_API_KEY`: Lấy từ [LangSmith](https://smith.langchain.com/) (để debug/tracing)

#### 5. Khởi động PostgreSQL (chỉ database)
```bash
docker-compose up -d postgres
# Hoặc: start_postgres.bat
```

#### 6. Load dữ liệu (nếu chưa có)
```bash
python migrate_to_postgres.py
python -m rag.initialize_rag
```

#### 7. Chạy Streamlit app
```bash
streamlit run app.py
```

Truy cập: http://localhost:8501

---

## 🎯 Lựa chọn cách chạy

| Tình huống | Khuyến nghị |
|------------|-------------|
| **Lần đầu chạy / Demo** | 🐳 Docker (Cách 1) |
| **Chạy cho nhóm xem** | 🐳 Docker (Cách 1) |
| **Đang develop/sửa code** | 🐍 Python (Cách 2) |
| **Deploy lên server** | 🐳 Docker (Cách 1) |

## 🎯 Sử dụng

### Text-to-SQL Chat
Hỏi bằng tiếng Anh tự nhiên:
- "How many warehouses are there?"
- "What are the top 5 products by revenue?"
- "Which warehouse has the most inventory?"
- "Show sales by customer type"
- "What is the total inventory value?"

### SQL Console
Chạy SQL trực tiếp:
```sql
SELECT COUNT(*) FROM warehouses;
SELECT city, province FROM warehouses;
SELECT sku_name, current_inventory_quantity FROM inventory_summary LIMIT 10;
```

### Database Connection Test
Click "Check DB" trong sidebar để kiểm tra kết nối.

## 🔧 Cấu hình

### Database Settings
- **Host**: localhost:5432
- **Database**: inventory_db
- **User**: inventory_user
- **Password**: inventory_pass

### Model Settings
- **Default Model**: llama-3.1-70b-versatile
- **Temperature**: 0.1 (cho consistency)
- **Top-k**: 3 (số examples retrieved)

### RAG Settings
- Hệ thống RAG nay đọc cấu hình từ `configs/settings.py` (có thể override qua biến môi trường):
  - `INV_RAG_EMBEDDING_MODEL` (mặc định: `all-MiniLM-L6-v2`)
  - `INV_CHROMA_PERSIST_DIR` (mặc định: `data/chroma_db`)
  - `INV_RAG_TOP_K` (mặc định: `2`)
  - `INV_RAG_SIMILARITY_THRESHOLD` (mặc định: `0.3`)

Ví dụ `.env`:
```env
# RAG
INV_RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
INV_CHROMA_PERSIST_DIR=data/chroma_db
INV_RAG_TOP_K=3
INV_RAG_SIMILARITY_THRESHOLD=0.35
```

Lưu ý:
- Sau khi đổi cấu hình RAG hoặc cập nhật `data/examples.jsonl`, dùng nút "Rebuild RAG Index" ở sidebar để xây lại chỉ mục.
- `sentence-transformers` cần `torch`. Trên Windows nếu thiếu, cài `torch` CPU: `pip install torch --index-url https://download.pytorch.org/whl/cpu`.

## 📁 Cấu trúc project

```
📁 Multi-agent system inventory/
├── 🐳 docker-compose.yml          # PostgreSQL setup
├── 🗄️ init.sql                    # Database schema
├── 📊 migrate_to_postgres.py      # Data migration
├── 🤖 agents/                     # AI agents
│   ├── intent_agent.py           # Intent classification
│   ├── sql_agent.py              # SQL generation
│   ├── orchestrator.py           # Workflow coordination
│   ├── viz_agent.py              # Visualization
│   └── response_agent.py         # Response formatting
├── 📊 data/                       # Data files
│   ├── warehouse.csv             # Warehouse data
│   ├── sku.csv                   # Product data
│   ├── inventory.csv             # Inventory data
│   ├── sales.csv                 # Sales data
│   ├── examples.jsonl            # Example Q&A pairs
│   └── metadata_db.yml           # Database metadata
├── 🔗 db/connection.py            # Database connections
├── 🧠 rag/                        # RAG system
├── ⚙️ configs/settings.py         # Configuration
├── 🛠️ utils/logger.py            # Logging utilities
└── 🖥️ app.py                      # Streamlit interface
```

## 🚨 Troubleshooting

### Docker không chạy được
```bash
# Kiểm tra Docker Desktop đã chạy chưa
docker --version

# Xem logs
docker-compose logs -f

# Reset và chạy lại
docker-compose down
docker-compose up -d --build
```

### PostgreSQL không kết nối được
```bash
# Kiểm tra container
docker ps

# Restart container
docker-compose restart postgres

# Xem logs
docker logs inventory_postgres

# Vào database test
docker exec -it inventory_postgres psql -U inventory_user -d inventory_db
```

### GROQ API Key lỗi
- Kiểm tra file `.env` có đúng format và có `GROQ_API_KEY=gsk_...`
- Verify API key tại https://console.groq.com/keys
- Restart: `docker-compose restart app`

### Data không load được
```bash
# Chạy migration manually
docker exec -it inventory_app python migrate_to_postgres.py

# Kiểm tra data
docker exec inventory_postgres psql -U inventory_user -d inventory_db -c "SELECT COUNT(*) FROM warehouses;"
```

### RAG system lỗi
```bash
# Rebuild RAG trong container
docker exec -it inventory_app python -m rag.initialize_rag

# Hoặc nhấn "Rebuild RAG Index" trong app
```

### Port 8501 đã được sử dụng
Sửa `docker-compose.yml`:
```yaml
ports:
  - "8502:8501"  # Đổi từ 8501 sang 8502
```

## 🔄 Dừng hệ thống

### Nếu chạy bằng Docker:
```bash
docker-compose down
# Hoặc: docker-stop.bat
```

### Nếu chạy bằng Python:
```bash
# Dừng Streamlit: Ctrl+C trong terminal

# Dừng PostgreSQL
docker-compose down
# Hoặc: stop_postgres.bat
```

### Reset toàn bộ (xóa cả data):
```bash
docker-compose down -v
```

## 📈 Performance

- **Database**: PostgreSQL với indexes tối ưu
- **AI Model**: Groq Llama 3.1 70B (nhanh)
- **Caching**: Streamlit cache cho orchestrator
- **Connection Pooling**: SQLAlchemy engine

## 🎯 Ví dụ câu hỏi

### Đơn giản
- "How many warehouses are there?" → 4
- "List all cities with warehouses" → Regina, Saskatoon, Montreal, Quebec City
- "What is the total inventory value?" → $X,XXX,XXX

### Phức tạp
- "Show top 5 products by revenue in the last quarter"
- "Which warehouse has the highest inventory turnover?"
- "Compare sales performance between customer types"
- "Find products with low stock levels"

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

MIT License - xem file LICENSE để biết thêm chi tiết.

## 📞 Support

Nếu gặp vấn đề, tạo issue trên GitHub hoặc liên hệ qua email.

---

**🎉 Chúc bạn sử dụng hệ thống hiệu quả!**