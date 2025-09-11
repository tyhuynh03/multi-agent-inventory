import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from agents.sql_agent import generate_sql
from agents.viz_agent import render_auto_chart
from db.connection import get_db, run_sql, run_sqlite
from configs.settings import DEFAULT_DB_PATH, DEFAULT_MODEL, DEFAULT_EXAMPLES_PATH, RAG_TOP_K

# NEW: plotting for auto-visualize
import matplotlib.pyplot as plt
import numpy as np

# LangSmith traceable (optional)
try:
    from langsmith.run_helpers import traceable
except Exception:
    def traceable(*args, **kwargs):
        def deco(fn):
            return fn
        return deco

load_dotenv()

st.set_page_config(page_title="Multi-Agent for Inventory", layout="wide")

st.title("🤖 Multi-Agent for Inventory (SQLite + LangChain, Groq)")

# --- Helpers ---
VISUALIZE_KEYWORDS = [
    "chart", "plot", "visualize", "visualise", "trend", "over time", "by month", "by week",
    "by category", "compare", "vs", "distribution", "time series"
]

@traceable(name="intent.classify")
def is_visualize_intent(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in VISUALIZE_KEYWORDS)


@traceable(name="sql.exec")
def exec_sql_with_fallback(db, db_path: str, sql: str):
    df, err = run_sql(db, sql)
    if err and "engine is not available" in err:
        df, err = run_sqlite(db_path, sql)
    return {"df": df, "error": err}


@traceable(name="agent.orchestrate")
def orchestrate(question: str, db_path: str, model: str, use_retriever: bool, examples_path: str, top_k: int, show_debug: bool):
    intent_visualize = is_visualize_intent(question)
    db = get_db(db_path)
    # Generate SQL
    result = generate_sql(
        question,
        db,
        model=model,
        examples_path=examples_path,
        top_k=top_k,
        return_debug=show_debug,
    )
    if show_debug:
        sql, debug = result  # type: ignore
    else:
        sql = result  # type: ignore
        debug = None
    # Execute
    exec_result = exec_sql_with_fallback(db, db_path, sql)
    df, err = exec_result["df"], exec_result["error"]
    return {"intent_visualize": intent_visualize, "sql": sql, "df": df, "error": err, "debug": debug}

with st.sidebar:
    st.header("Settings")
    db_path = st.text_input("SQLite path", value=DEFAULT_DB_PATH)
    model = st.text_input("Groq model", value=DEFAULT_MODEL)
    use_retriever = st.checkbox("Use retrieved few-shot (RAG)", value=False)
    examples_path = st.text_input("Examples JSONL path", value=DEFAULT_EXAMPLES_PATH)
    top_k = st.number_input("Top-k retrieved examples", min_value=1, max_value=10, value=RAG_TOP_K, step=1)
    show_debug = st.checkbox("Show debug info", value=False)
    auto_visualize = st.checkbox("Auto visualize when possible", value=True)
    if st.button("Check DB connection"):
        try:
            db = get_db(db_path)
            st.success("Connected. Tables:")
            st.code(db.get_usable_table_names(), language="bash")
        except Exception as e:
            st.error(f"DB error: {e}")

# Tabs: Text-to-SQL and SQL Console
# Keeping a single chat-like flow in Text-to-SQL and show charts under results.
tab_text2sql, tab_sql_console = st.tabs(["Text-to-SQL", "SQL Console"]) 

with tab_text2sql:
    st.write("Enter your question in English. The app will generate a `SELECT` query and run it on SQLite.")
    question = st.text_area("Question / Request", height=120, placeholder="e.g., Trend of total inventory for store S001 over time.")

    col1, col2 = st.columns([1, 3])
    with col1:
        run_clicked = st.button("Run Agent")
    with col2:
        show_schema = st.checkbox("Show schema", value=True, key="schema_text2sql")

    if run_clicked:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                if show_schema:
                    db = get_db(db_path)
                    st.subheader("Schema")
                    st.code(db.get_table_info(), language="sql")

                outcome = orchestrate(
                    question=question,
                    db_path=db_path,
                    model=model,
                    use_retriever=use_retriever,
                    examples_path=examples_path,
                    top_k=top_k,
                    show_debug=show_debug,
                )
                sql = outcome["sql"]
                df = outcome["df"]
                err = outcome["error"]
                st.subheader("Generated SQL")
                st.code(sql, language="sql")
                if show_debug and outcome["debug"] is not None:
                    st.subheader("Debug Info")
                    st.json(outcome["debug"]) 
                if err:
                    st.error(err)
                else:
                    st.subheader("Results")
                    st.dataframe(df, use_container_width=True)
                    st.caption(f"Rows: {len(df)}")
                    if auto_visualize or outcome["intent_visualize"]:
                        fig = render_auto_chart(df)
                        if fig:
                            st.pyplot(fig)
            except Exception as e:
                st.error(str(e))

with tab_sql_console:
    st.write("Run your own SQL (SELECT-only) against SQLite.")
    sql_text = st.text_area("SQL", height=160, placeholder='SELECT "Product ID", "Inventory Level" FROM inventory LIMIT 10')
    colc1, colc2 = st.columns([1, 3])
    with colc1:
        run_sql_btn = st.button("Run SQL")
    with colc2:
        show_schema_sql = st.checkbox("Show schema", value=False, key="schema_sql_console")

    if run_sql_btn:
        if not sql_text.strip():
            st.warning("Please enter a SQL query.")
        elif not sql_text.strip().lower().startswith("select"):
            st.error("Only SELECT statements are allowed for safety.")
        else:
            try:
                db = get_db(db_path)
                if show_schema_sql:
                    st.subheader("Schema")
                    st.code(db.get_table_info(), language="sql")

                df, err = run_sql(db, sql_text)
                if err and "engine is not available" in err:
                    df, err = run_sqlite(db_path, sql_text)
                if err:
                    st.error(err)
                else:
                    st.subheader("Results")
                    st.code(sql_text, language="sql")
                    st.dataframe(df, use_container_width=True)
                    st.caption(f"Rows: {len(df)}")
            except Exception as e:
                st.error(str(e))
