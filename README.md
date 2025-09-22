# 🤖 Multi-Agent Inventory Management System

Hệ thống quản lý kho hàng thông minh sử dụng Multi-Agent AI với PostgreSQL, LangChain và Groq.

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

## 🛠️ Cài đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd "Multi-agent system inventory"
```

### 2. Tạo virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Tạo file .env
Tạo file `.env` với nội dung:
```env
# Groq API Key - Get from https://console.groq.com/keys
GROQ_API_KEY=your_actual_groq_api_key_here

# Database settings
DEFAULT_DB_PATH=data/inventory.db
DEFAULT_MODEL=llama-3.1-70b-versatile
DEFAULT_EXAMPLES_PATH=data/examples.jsonl
RAG_TOP_K=3
```

**Lấy GROQ_API_KEY:**
1. Truy cập: https://console.groq.com/keys
2. Đăng ký/Đăng nhập tài khoản
3. Tạo API key mới
4. Copy và thay thế `your_actual_groq_api_key_here`

## 🐳 Chạy hệ thống

### 1. Khởi động PostgreSQL
```bash
# Sử dụng Docker Compose
docker-compose up -d postgres

# Hoặc chạy script
start_postgres.bat
```

### 2. Kiểm tra PostgreSQL
```bash
# Kiểm tra container
docker ps

# Kết nối database
docker exec -it inventory_postgres psql -U inventory_user -d inventory_db
```

### 3. Load dữ liệu (nếu chưa có)
```bash
python migrate_to_postgres.py
```

### 4. Chạy Streamlit app
```bash
python -m streamlit run app.py
```

Truy cập: http://localhost:8501

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
│   ├── report_agent.py           # Report generation
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

### PostgreSQL không kết nối được
```bash
# Kiểm tra container
docker ps

# Restart container
docker-compose restart postgres

# Xem logs
docker logs inventory_postgres
```

### GROQ API Key lỗi
- Kiểm tra file `.env` có đúng format
- Verify API key tại https://console.groq.com/keys
- Restart Streamlit app

### Lỗi pandas warning
- Đã được sửa bằng SQLAlchemy
- Nếu vẫn có warning, restart app

### RAG system lỗi
- Tạm thời disable semantic search trong sidebar
- Sẽ sửa trong version tiếp theo

## 🔄 Dừng hệ thống

```bash
# Dừng Streamlit (Ctrl+C trong terminal)

# Dừng PostgreSQL
docker-compose down

# Hoặc chạy script
stop_postgres.bat
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