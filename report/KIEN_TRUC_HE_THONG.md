# MÔ TẢ KIẾN TRÚC HỆ THỐNG MULTI-AGENT INVENTORY MANAGEMENT

## 1. TỔNG QUAN KIẾN TRÚC

Hệ thống được xây dựng theo kiến trúc **Multi-Agent System** với mô hình **Orchestrator Pattern**, sử dụng **LLM (Large Language Model)** để xử lý ngôn ngữ tự nhiên và **RAG (Retrieval-Augmented Generation)** để cải thiện độ chính xác của SQL generation.

### 1.1. Kiến trúc tổng thể (3-Layer Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│              Streamlit Web Interface (app.py)                │
│  - Chat Interface                                           │
│  - Query Results Display                                    │
│  - Visualization Charts                                     │
│  - Session Management & Caching                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                      │
│              Orchestrator Agent (orchestrator.py)             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Intent Classification Agent                         │   │
│  │  SQL Generation Agent                                │   │
│  │  Analytics Agent                                     │   │
│  │  Visualization Agent                                  │   │
│  │  Response Agent                                       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      DATA LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │  RAG System   │  │  Examples   │      │
│  │  Database    │  │  (ChromaDB)   │  │  (JSONL)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 2. CÁC THÀNH PHẦN CHÍNH

### 2.1. Presentation Layer (Lớp Giao diện)

**File:** `app.py`

**Chức năng:**
- Cung cấp giao diện web tương tác cho người dùng
- Quản lý session state và chat history
- Hiển thị kết quả truy vấn (bảng dữ liệu, biểu đồ)
- Cache query results để tối ưu hiệu năng
- Lưu trữ conversation vào file JSON

**Công nghệ:** Streamlit Framework

### 2.2. Business Logic Layer (Lớp Logic Nghiệp vụ)

#### 2.2.1. Orchestrator Agent (Điều phối viên)

**File:** `agents/orchestrator.py`

**Vai trò:** Điều phối workflow, quyết định routing giữa các agent

**Luồng xử lý:**
1. Nhận câu hỏi từ người dùng
2. Gọi Intent Classification Agent để phân loại ý định
3. Dựa trên intent, route đến agent phù hợp:
   - `query` → SQL Generation Agent
   - `visualize` → SQL Generation Agent + Visualization Agent
   - `schema` → Schema Information Handler
   - `inventory_analytics` → Analytics Agent
4. Tổng hợp kết quả và trả về Presentation Layer

#### 2.2.2. Intent Classification Agent

**File:** `agents/intent_agent.py`

**Chức năng:**
- Phân loại câu hỏi người dùng thành 4 loại intent:
  - `query`: Câu hỏi truy vấn dữ liệu thông thường
  - `visualize`: Yêu cầu tạo biểu đồ
  - `schema`: Câu hỏi về cấu trúc database
  - `inventory_analytics`: Phân tích nâng cao (Stock Cover Days)

**Input:** Câu hỏi người dùng (natural language)
**Output:** 
```json
{
  "intent": "query|visualize|schema|inventory_analytics",
  "confidence": 0.95,
  "reasoning": "Explanation of classification"
}
```

**Công nghệ:** LLM (Groq API) với structured prompt

#### 2.2.3. SQL Generation Agent

**File:** `agents/sql_agent.py`

**Chức năng:**
- Chuyển đổi câu hỏi ngôn ngữ tự nhiên thành SQL query
- Sử dụng RAG để retrieve similar examples từ `examples.jsonl`
- Inject database schema metadata vào prompt
- Validate và extract SQL từ LLM response

**Quy trình:**
1. **RAG Retrieval:** Tìm top-k examples tương tự từ vector database (ChromaDB)
2. **Schema Context:** Load metadata từ `metadata_db.yml` (tables, columns, descriptions)
3. **Prompt Construction:** 
   - System prompt từ `prompts/sql_prompt.txt`
   - Few-shot examples từ RAG
   - Schema context
   - User question
4. **LLM Generation:** Gọi LLM (Groq) để sinh SQL
5. **SQL Extraction:** Parse SQL từ response (code block hoặc raw SQL)

**Input:** Câu hỏi người dùng, database connection, examples path
**Output:** SQL query string

**Công nghệ:** 
- LLM: Groq API (model: `openai/gpt-oss-20b`)
- RAG: ChromaDB vector database
- LangChain: SQLDatabase wrapper

#### 2.2.4. Analytics Agent

**File:** `agents/analytics_agent.py`

**Chức năng:**
- Tính toán các metrics nâng cao:
  - **Stock Cover Days:** Số ngày tồn kho còn lại dựa trên tốc độ bán hàng
  - **Stock Status:** Phân loại (Critical, Warning, Healthy, Good, Overstock)
  - **Stockout Risk:** Đánh giá rủi ro hết hàng (At Risk, Warning, Safe)
- Tạo báo cáo phân tích tự động

**Công thức Stock Cover Days:**
```
Stock Cover Days = Current Inventory Quantity / Average Daily Sales
Average Daily Sales = Total Quantity Sold (30 days) / 30
```

**Input:** Database connection
**Output:** DataFrame với các cột:
- `sku_id`, `sku_name`, `warehouse_id`
- `current_inventory_quantity`
- `avg_daily_sales`, `active_days`, `total_quantity_sold`
- `stock_cover_days`
- `stock_status`, `stockout_risk`

**Công nghệ:** PostgreSQL queries với CTEs (Common Table Expressions)

#### 2.2.5. Visualization Agent

**File:** `agents/viz_agent.py`

**Chức năng:**
- Tự động chọn loại biểu đồ phù hợp dựa trên dữ liệu
- Tạo visualization với Plotly
- Hỗ trợ các loại biểu đồ: Bar, Line, Pie, Scatter, Heatmap

**Quy trình:**
1. **Chart Planning:** LLM phân tích dữ liệu và đề xuất loại biểu đồ
2. **Chart Rendering:** Tạo Plotly figure với specifications
3. **Return:** Plotly figure object

**Input:** Câu hỏi người dùng, DataFrame
**Output:** Plotly figure object

**Công nghệ:** 
- LLM: Groq API (để plan chart type)
- Plotly: Để render charts

#### 2.2.6. Response Agent

**File:** `agents/response_agent.py`

**Chức năng:**
- Tạo câu trả lời ngôn ngữ tự nhiên từ kết quả truy vấn
- Format dữ liệu dạng markdown table
- Tóm tắt kết quả một cách ngắn gọn

**Input:** Câu hỏi người dùng, DataFrame, SQL query (optional)
**Output:** 
```json
{
  "text": "Natural language summary",
  "table_md": "Markdown formatted table"
}
```

**Công nghệ:** LLM (Groq API) với structured prompt

### 2.3. Data Layer (Lớp Dữ liệu)

#### 2.3.1. PostgreSQL Database

**File:** `init.sql`, `db/connection.py`

**Schema:**
- **warehouses:** Thông tin kho hàng (warehouse_code, city, province, country)
- **skus:** Thông tin sản phẩm (sku_id, sku_name, category)
- **inventory:** Tồn kho hiện tại (sku_id, warehouse_id, current_inventory_quantity, average_lead_time_days, total_value)
- **sales:** Dữ liệu bán hàng (order_date, sku_id, warehouse_id, order_quantity, revenue)

**Views:**
- `inventory_summary`: Tổng hợp inventory + SKU + warehouse
- `sales_summary`: Tổng hợp sales + SKU + warehouse
- `stock_cover_analysis`: Phân tích stock cover days (pre-calculated)

**Công nghệ:** PostgreSQL 15+ với Docker

#### 2.3.2. RAG System (Retrieval-Augmented Generation)

**Files:** `rag/rag_retriever.py`, `rag/initialize_rag.py`

**Chức năng:**
- Lưu trữ và tìm kiếm semantic các SQL examples
- Cải thiện độ chính xác SQL generation bằng few-shot learning

**Quy trình:**
1. **Initialization:** 
   - Load examples từ `data/examples.jsonl`
   - Generate embeddings cho mỗi example (question + SQL)
   - Lưu vào ChromaDB vector database
2. **Retrieval:**
   - Embed user question
   - Tìm top-k examples tương tự nhất (cosine similarity)
   - Trả về examples để inject vào prompt

**Công nghệ:**
- Vector Database: ChromaDB
- Embedding Model: Default ChromaDB embedding (có thể config)

**Data Source:** `data/examples.jsonl` (JSON Lines format)
```json
{"question": "How many products are in stock?", "sql": "SELECT COUNT(*) FROM inventory WHERE current_inventory_quantity > 0"}
```

#### 2.3.3. Metadata & Examples

**Files:** 
- `data/metadata_db.yml`: Database schema metadata
- `data/examples.jsonl`: SQL examples cho RAG

## 3. LUỒNG XỬ LÝ CHI TIẾT

### 3.1. Luồng xử lý Query Intent

```
User Question
    │
    ▼
┌─────────────────────┐
│  Streamlit App      │
│  (app.py)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Orchestrator Agent │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Intent Agent       │───► LLM (Groq)
│  classify_intent()  │
└──────────┬──────────┘
           │
           ▼ (intent = "query")
┌─────────────────────┐
│  SQL Generation     │
│  Agent              │
│  ┌───────────────┐ │
│  │ RAG Retrieval │ │───► ChromaDB
│  │ (top-k)       │ │
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ Schema Context│ │───► metadata_db.yml
│  └───────────────┘ │
│  ┌───────────────┐ │
│  │ LLM Generate  │ │───► Groq API
│  │ SQL           │ │
│  └───────────────┘ │
└──────────┬──────────┘
           │
           ▼ (SQL query)
┌─────────────────────┐
│  Database           │
│  Execute SQL        │───► PostgreSQL
└──────────┬──────────┘
           │
           ▼ (DataFrame)
┌─────────────────────┐
│  Response Agent     │───► LLM (Groq)
│  generate_response()│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Streamlit Display   │
│  - Text Response     │
│  - Data Table        │
└─────────────────────┘
```

### 3.2. Luồng xử lý Visualize Intent

```
User Question
    │
    ▼
Orchestrator → Intent Agent → (intent = "visualize")
    │
    ▼
SQL Generation Agent → Database → DataFrame
    │
    ▼
Visualization Agent
    │
    ├─► LLM (Plan chart type)
    │
    └─► Plotly (Render chart)
    │
    ▼
Streamlit Display
    - Chart
    - Data Table
```

### 3.3. Luồng xử lý Inventory Analytics Intent

```
User Question
    │
    ▼
Orchestrator → Intent Agent → (intent = "inventory_analytics")
    │
    ▼
Analytics Agent
    │
    ├─► calculate_stock_cover_days()
    │   └─► PostgreSQL (Complex CTE query)
    │
    ├─► Filter based on question (critical/warning/top N)
    │
    └─► generate_analytics_report()
        └─► LLM (Groq) - Natural language summary
    │
    ▼
Streamlit Display
    - Analytics Summary
    - Data Table (Stock Cover Days)
```

## 4. CÁC THÀNH PHẦN HỖ TRỢ

### 4.1. Configuration

**File:** `configs/settings.py`

**Nội dung:**
- Database connection settings
- LLM model configuration (Groq API key, model name)
- RAG settings (top_k, examples path)
- Default paths

### 4.2. Database Connection

**File:** `db/connection.py`

**Chức năng:**
- Quản lý kết nối PostgreSQL
- Unified SQL execution function (`run_sql_unified`)
- Hỗ trợ cả PostgreSQL và SQLite (legacy)

### 4.3. Logging & Tracing

**File:** `utils/logger.py`

**Chức năng:**
- LangSmith integration cho tracing
- Debug logging

## 5. SƠ ĐỒ KIẾN TRÚC TỔNG THỂ (ĐỂ VẼ)

### 5.1. Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │     Streamlit Web Interface           │
        │         (app.py)                       │
        │  - Chat Input                          │
        │  - Results Display                     │
        │  - Charts                              │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │      Orchestrator Agent                │
        │    (orchestrator.py)                   │
        │  ┌─────────────────────────────────┐ │
        │  │ Intent Classification Agent       │ │
        │  └─────────────────────────────────┘ │
        └───────┬───────────┬───────────┬───────┘
                │           │           │
        ┌───────▼───┐  ┌───▼────┐  ┌───▼──────────┐
        │ SQL Agent │  │Analytics│  │Viz Agent    │
        │           │  │ Agent  │  │             │
        └───────┬───┘  └───┬────┘  └───┬──────────┘
                │          │           │
        ┌───────▼──────────▼───────────▼──────────┐
        │      Response Agent                   │
        └───────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌─────────────┐  ┌──────────┐  ┌─────────────┐
│ PostgreSQL  │  │  RAG     │  │   LLM       │
│  Database   │  │ (ChromaDB)│  │  (Groq API) │
└─────────────┘  └──────────┘  └─────────────┘
```

### 5.2. Sequence Diagram (Query Flow)

```
User    Streamlit    Orchestrator    Intent    SQL Agent    RAG    Database    Response
 │          │             │             │          │        │        │           │
 │──Question─►             │             │          │        │        │           │
 │          │             │             │          │        │        │           │
 │          │──question──►             │          │        │        │           │
 │          │             │             │          │        │        │           │
 │          │             │──classify──►          │        │        │           │
 │          │             │             │          │        │        │           │
 │          │             │◄─intent────│          │        │        │           │
 │          │             │             │          │        │        │           │
 │          │             │──generate───┼──────────►        │        │           │
 │          │             │             │          │        │        │           │
 │          │             │             │          │──retrieve──►    │           │
 │          │             │             │          │◄─examples─│    │           │
 │          │             │             │          │        │        │           │
 │          │             │             │          │──LLM───┼────────┼───────────┤
 │          │             │             │          │◄─SQL───┼────────┼───────────┤
 │          │             │             │          │        │        │           │
 │          │             │             │          │──execute───────►           │
 │          │             │             │          │        │        │           │
 │          │             │             │          │◄──DataFrame─────│           │
 │          │             │             │          │        │        │           │
 │          │             │──generate───┼──────────┼────────┼────────┼──────────►
 │          │             │             │          │        │        │           │
 │          │             │◄─response───┼──────────┼────────┼────────┼───────────┤
 │          │             │             │          │        │        │           │
 │          │◄─result─────│             │          │        │        │           │
 │          │             │             │          │        │        │           │
 │◄─Display─│             │             │          │        │        │           │
```

## 6. ĐẶC ĐIỂM KỸ THUẬT

### 6.1. Công nghệ sử dụng

- **Frontend:** Streamlit (Python web framework)
- **Backend:** Python 3.10+
- **LLM:** Groq API (model: `openai/gpt-oss-20b`)
- **Database:** PostgreSQL 15+
- **Vector DB:** ChromaDB
- **Visualization:** Plotly
- **Deployment:** Docker + Docker Compose

### 6.2. Kiến trúc pattern

- **Orchestrator Pattern:** Orchestrator Agent điều phối các agent khác
- **Agent Pattern:** Mỗi agent có trách nhiệm chuyên biệt
- **RAG Pattern:** Retrieval-Augmented Generation để cải thiện SQL generation
- **Few-shot Learning:** Sử dụng examples từ RAG để guide LLM

### 6.3. Data Flow

1. **User Input** → Natural Language Question
2. **Intent Classification** → Intent type + confidence
3. **Agent Routing** → Specific agent based on intent
4. **SQL Generation** (if needed) → SQL query
5. **Database Execution** → DataFrame
6. **Post-processing** → Analytics/Visualization/Response
7. **Output** → Natural language + Data/Chart

## 7. HƯỚNG DẪN VẼ SƠ ĐỒ

### 7.1. Tools đề xuất

- **Draw.io / diagrams.net:** Miễn phí, hỗ trợ nhiều loại diagram
- **Lucidchart:** Professional, có template sẵn
- **PlantUML:** Code-based, dễ version control
- **Mermaid:** Markdown-based, tích hợp tốt với documentation

### 7.2. Các loại sơ đồ nên vẽ

1. **Architecture Diagram (Component Diagram):** 
   - Hiển thị các thành phần và mối quan hệ
   - Sử dụng boxes cho components, arrows cho data flow

2. **Sequence Diagram:**
   - Hiển thị luồng xử lý theo thời gian
   - Useful cho query flow và visualize flow

3. **Data Flow Diagram:**
   - Hiển thị luồng dữ liệu từ input đến output
   - Có thể kết hợp với architecture diagram

4. **Deployment Diagram:**
   - Hiển thị cách hệ thống được deploy (Docker containers)

### 7.3. Màu sắc và ký hiệu đề xuất

- **Blue:** User Interface / Presentation Layer
- **Green:** Business Logic / Agents
- **Yellow:** Data Layer / Database
- **Orange:** External Services (LLM API)
- **Purple:** RAG / Vector Database

**Ký hiệu:**
- **Rectangle:** Component / Agent
- **Cylinder:** Database
- **Cloud:** External Service / API
- **Arrow:** Data Flow / Communication

---

**Lưu ý:** Mô tả này dựa trên codebase hiện tại. Bạn có thể điều chỉnh các sơ đồ để phù hợp với style báo cáo của mình.

