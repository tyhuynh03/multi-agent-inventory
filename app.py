import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from text_to_sql import get_db, generate_sql, run_sql, run_sqlite

load_dotenv()

st.set_page_config(page_title="Text-to-SQL (SQLite)", layout="wide")

st.title("🔎 Text-to-SQL for Inventory (SQLite + LangChain, Groq)")

with st.sidebar:
    st.header("Settings")
    db_path = st.text_input("SQLite path", value="inventory.db")
    model = st.text_input("Groq model", value="openai/gpt-oss-20b")
    use_retriever = st.checkbox("Use retrieved few-shot (RAG)", value=False)
    examples_path = st.text_input("Examples JSONL path", value="examples.jsonl")
    top_k = st.number_input("Top-k retrieved examples", min_value=1, max_value=10, value=4, step=1)
    show_debug = st.checkbox("Show debug info", value=False)
    if st.button("Check DB connection"):
        try:
            db = get_db(db_path)
            st.success("Connected. Tables:")
            st.code(db.get_usable_table_names(), language="bash")
        except Exception as e:
            st.error(f"DB error: {e}")

# Tabs: Text-to-SQL and SQL Console
tab_text2sql, tab_sql_console = st.tabs(["Text-to-SQL", "SQL Console"]) 

with tab_text2sql:
    st.write("Enter your question in English. The app will generate a `SELECT` query and run it on SQLite.")
    question = st.text_area("Question / Request", height=120, placeholder="e.g., List the 10 products with the lowest inventory quantity.")

    col1, col2 = st.columns([1, 3])
    with col1:
        run_clicked = st.button("Generate SQL & Run")
    with col2:
        show_schema = st.checkbox("Show schema", value=True, key="schema_text2sql")

    if run_clicked:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                db = get_db(db_path)
                if show_schema:
                    st.subheader("Schema")
                    st.code(db.get_table_info(), language="sql")

                if show_debug:
                    result = generate_sql(
                        question,
                        db,
                        model=model,
                        use_retriever=use_retriever,
                        examples_path=examples_path,
                        top_k=top_k,
                        return_debug=True,
                    )
                    sql, debug = result  # type: ignore
                    st.subheader("Generated SQL")
                    st.code(sql, language="sql")
                    st.subheader("Debug Info")
                    st.json(debug)
                else:
                    sql = generate_sql(
                        question,
                        db,
                        model=model,
                        use_retriever=use_retriever,
                        examples_path=examples_path,
                        top_k=top_k,
                    )
                    st.subheader("Generated SQL")
                    st.code(sql, language="sql")

                df, err = run_sql(db, sql)
                if err and "engine is not available" in err:
                    df, err = run_sqlite(db_path, sql)
                if err:
                    st.error(err)
                else:
                    st.subheader("Results")
                    st.dataframe(df, use_container_width=True)
                    st.caption(f"Rows: {len(df)}")
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
