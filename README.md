# Text-to-SQL (SQLite) for Inventory — Groq-only

## Requirements
- Python 3.10+
- Groq API key

## Install
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Prepare data
```bash
python load_csv_to_sqlite.py retail_store_inventory.csv --db inventory.db --table inventory
```

## Configure API key
Create a `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```

## Run UI
```bash
streamlit run app.py
```
- Set SQLite path (default `inventory.db`).
- Choose Groq model (default `openai/gpt-oss-20b`).
- Ask your question in English; the app generates a `SELECT` and executes it.

## Notes
- Only `SELECT` queries are allowed for safety.
- Works with quoted identifiers like "Product ID" in SQLite.
