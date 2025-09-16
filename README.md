# 🤖 Multi-Agent Inventory Management System

A sophisticated **Text-to-SQL + Visualization** system built with **LangChain** and **Groq LLM**. This multi-agent architecture provides intelligent inventory analysis through natural language queries, automatic chart generation, and comprehensive reporting capabilities.

## ✨ Key Features

### 🧠 **Intelligent Multi-Agent Architecture**
- **Intent Classification Agent**: Automatically detects user intent (query, visualize, report, schema)
- **SQL Agent**: Generates accurate SQL queries from natural language using RAG few-shot learning
- **Visualization Agent**: Creates interactive charts (Plotly/Matplotlib) with intelligent chart type selection
- **Report Agent**: Generates structured business reports (low stock, top products, category analysis)
- **Response Agent**: Provides natural language summaries of query results
- **Orchestrator Agent**: Coordinates workflow between all agents

### 🔍 **Advanced Capabilities**
- **Advanced RAG with ChromaDB**: Semantic search using vector embeddings for intelligent example retrieval
- **Semantic Similarity**: Finds most relevant SQL examples based on question meaning, not just keywords
- **Auto-Visualization**: Intelligent chart type selection (line charts for time series, bar charts for categories)
- **Schema-Aware**: Uses YAML metadata for enhanced SQL generation accuracy
- **LangSmith Tracing**: Optional observability and debugging support
- **Safety-First**: SELECT-only queries to prevent data corruption
- **Fallback System**: Graceful degradation to simple retrieval if semantic search fails

### 📊 **Business Intelligence**
- **Inventory Analysis**: Stock levels, sales performance, demand forecasting
- **Category Performance**: Product category breakdowns and comparisons
- **Low Stock Alerts**: Automated identification of products needing restocking
- **Revenue Analysis**: Sales performance and product profitability insights
- **Overstock Detection**: Identification of excess inventory

## 🏗️ Project Architecture

```
SQL_AGENT/
├── agents/                    # Multi-agent system
│   ├── orchestrator.py       # Main workflow coordinator
│   ├── intent_agent.py       # Intent classification
│   ├── sql_agent.py          # SQL generation with RAG
│   ├── viz_agent.py          # Chart planning & rendering
│   ├── report_agent.py       # Business report generation
│   └── response_agent.py     # Natural language responses
├── rag/                      # RAG system with ChromaDB
│   ├── rag_agent.py          # ChromaDB-based semantic search
│   ├── initialize_rag.py     # RAG initialization script
│   ├── rebuild_rag.py        # RAG rebuild script
│   └── demo_rag_comparison.py # RAG comparison demo
├── configs/
│   └── settings.py           # Configuration management
├── db/
│   └── connection.py         # SQLite database operations
├── data/
│   ├── inventory.db          # SQLite database
│   ├── examples.jsonl        # RAG few-shot examples
│   ├── metadata_db.yml       # Database schema metadata
│   ├── chroma_db/            # ChromaDB vector storage (auto-generated, gitignored)
│   └── retail_store_inventory.csv
├── prompts/
│   └── sql_prompt.txt        # SQL generation template
├── utils/
│   └── logger.py             # Logging and tracing utilities
└── app.py                    # Streamlit web interface
```

## 🚀 Quick Start

### 1. **Environment Setup**
```bash
# Clone the repository
git clone <repository-url>
cd SQL_AGENT

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. **Database Setup**
```bash
# Load CSV data into SQLite
python load_csv_to_sqlite.py data/retail_store_inventory.csv --db data/inventory.db --table inventory
```

### 3. **API Configuration**
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
# Optional: LangSmith tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsm_...
LANGSMITH_PROJECT=inventory-text-to-sql
```

### 4. **Initialize RAG System** (Optional but Recommended)
```bash
# Initialize ChromaDB with semantic search
python rag/initialize_rag.py
```

### 5. **Launch Application**
```bash
streamlit run app.py
```

## 💡 Usage Examples

### **Natural Language Queries**
```
"What are the top 5 selling products this month?"
"Show me inventory levels for electronics category"
"Which products have low stock (less than 10 units)?"
"Generate a trend analysis for store S001 from January to March"
```

### **Visualization Requests**
```
"Create a chart showing sales trends over time"
"Visualize inventory levels by category"
"Show me a bar chart of top performing products"
```

### **Business Reports**
```
"Generate a low stock report for products below 15 units"
"Create a category performance summary"
"Show me inventory valuation by category"
"Generate an overstock alert for items above 100 units"
```

## 🔧 Configuration Options

### **Environment Variables**
- `INV_DB_PATH`: Database file path (default: `data/inventory.db`)
- `INV_MODEL`: Groq model name (default: `openai/gpt-oss-20b`)
- `INV_EXAMPLES_PATH`: RAG examples file (default: `data/examples.jsonl`)
- `INV_RAG_TOP_K`: Number of examples to retrieve (default: `2`)
- `INV_USE_SEMANTIC_SEARCH`: Enable ChromaDB semantic search (default: `true`)
- `INV_RAG_SIMILARITY_THRESHOLD`: Minimum similarity score (default: `0.3`)
- `INV_RAG_EMBEDDING_MODEL`: Sentence transformer model (default: `all-MiniLM-L6-v2`)
- `INV_CHROMA_PERSIST_DIR`: ChromaDB storage directory (default: `data/chroma_db`)
- `GROQ_API_KEY`: Your Groq API key

### **Supported Models**
- `openai/gpt-oss-20b` (default)
- `google/gemma-3-12b-it`
- `deepseek/deepseek-chat`
- Other Groq-compatible models

## 📈 Agent Capabilities

### **SQL Agent**
- Generates accurate SQLite queries from natural language
- **Advanced RAG**: ChromaDB-based semantic search for relevant examples
- **Semantic Similarity**: Finds most relevant examples based on question meaning
- Schema-aware with YAML metadata integration
- Automatic retry mechanism for failed queries
- Fallback to simple retrieval if semantic search fails

### **Visualization Agent**
- Intelligent chart type selection (line, bar)
- Automatic data aggregation and grouping
- Interactive Plotly charts with fallback to Matplotlib
- Time series detection and proper date handling

### **Report Agent**
- **Low Stock Reports**: Products below threshold
- **Top Products**: Best selling items by revenue/units
- **Category Summary**: Performance by product category
- **Inventory Valuation**: Total value by category
- **Overstock Alerts**: Products with excess inventory

### **Intent Classification**
- **Query**: Standard SQL queries
- **Visualize**: Chart generation requests
- **Report**: Business report generation
- **Schema**: Database structure information

## 🛡️ Safety Features

- **SELECT-only queries**: Prevents data modification
- **Input validation**: Sanitizes user inputs
- **Error handling**: Graceful failure with informative messages
- **SQL injection protection**: Parameterized queries

## 🧠 Advanced RAG System

### **ChromaDB Integration**
The system now uses ChromaDB for advanced semantic search capabilities:

```bash
# Initialize RAG system
python rag/initialize_rag.py

# Compare old vs new RAG systems
python rag/demo_rag_comparison.py

# Rebuild RAG index
python rag/rebuild_rag.py
```

### **RAG Features**
- **Semantic Search**: Uses sentence transformers to find semantically similar examples
- **Vector Embeddings**: Converts questions and examples to high-dimensional vectors
- **Similarity Scoring**: Configurable similarity thresholds for relevance filtering
- **Persistent Storage**: ChromaDB stores embeddings for fast retrieval
- **Fallback System**: Graceful degradation to simple retrieval if needed

### **RAG Configuration**
```env
# Enable/disable semantic search
INV_USE_SEMANTIC_SEARCH=true

# Similarity threshold (0.0 to 1.0)
INV_RAG_SIMILARITY_THRESHOLD=0.3

# Embedding model
INV_RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2

# ChromaDB storage location
INV_CHROMA_PERSIST_DIR=data/chroma_db
```

## 🔍 Monitoring & Debugging

### **LangSmith Integration** (Optional)
```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key
LANGSMITH_PROJECT=inventory-text-to-sql
```

### **Debug Mode**
Enable debug information in the Streamlit interface to see:
- Intent classification results
- SQL generation process
- Chart planning specifications
- Performance timing metrics

## 📊 Sample Data Schema

The system works with retail inventory data including:
- **Date**: Transaction date
- **Store ID**: Store identifier
- **Product ID**: Product identifier
- **Category**: Product category
- **Region**: Geographic region
- **Inventory Level**: Current stock quantity
- **Units Sold**: Sales volume
- **Units Ordered**: Purchase orders
- **Demand Forecast**: Predicted demand
- **Price**: Product price
- **Discount**: Applied discounts
- **Weather Condition**: Environmental factors
- **Holiday/Promotion**: Special events
- **Competitor Pricing**: Market pricing
- **Seasonality**: Seasonal patterns

## 🚧 Roadmap

### **Short Term**
- [ ] Enhanced SQL validation and auto-repair
- [ ] Advanced intent classification with skill registry
- [ ] Comprehensive test suite (pytest)
- [ ] Docker containerization

### **Medium Term**
- [ ] Multi-database support (PostgreSQL, MySQL)
- [ ] Advanced visualization types (heatmaps, scatter plots)
- [ ] Custom report templates
- [ ] API endpoints for integration

### **Long Term**
- [ ] Real-time data streaming
- [ ] Machine learning predictions
- [ ] Multi-language support
- [ ] Enterprise features (RBAC, audit logs)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangChain** for the agent framework
- **Groq** for high-performance LLM inference
- **Streamlit** for the web interface
- **Plotly** for interactive visualizations
- **SQLAlchemy** for database operations

---

**Built with ❤️ for intelligent inventory management**