import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from agents.orchestrator import OrchestratorAgent
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

# --- Initialize Orchestrator ---
@st.cache_resource
def get_orchestrator():
    return OrchestratorAgent()

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
        st.write("")  # Empty space for alignment

    if run_clicked:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                # Use Orchestrator Agent
                orchestrator = get_orchestrator()
                result = orchestrator.run_agent(
                    user_question=question,
                    db_path=db_path,
                    use_retriever=use_retriever,
                    examples_path=examples_path,
                    top_k=top_k
                )
                
                # Display intent classification
                st.subheader("🎯 Intent Classification")
                st.info(f"**Intent:** {result['intent']} | **Agent:** {result['agent']}")
                
                if not result["success"]:
                    st.error(f"❌ {result['error']}")
                else:
                    # Display SQL
                    st.subheader("Generated SQL")
                    st.code(result["sql"], language="sql")
                    
                    # Display results
                    st.subheader("Results")
                    st.success(result["message"])
                    
                    # Check if this is schema information
                    if "schema_info" in result and result["schema_info"]:
                        st.markdown(result["schema_info"])
                    elif result["data"] is not None:
                        st.dataframe(result["data"], use_container_width=True)
                        st.caption(f"Rows: {len(result['data'])}")
                    
                    # Display chart if available
                    if "chart" in result and result["chart"]:
                        st.subheader("📊 Visualization")
                        st.pyplot(result["chart"])
                    
                    # Display report summary if available
                    if "summary" in result and result["summary"]:
                        st.subheader("📋 Report Summary")
                        summary = result["summary"]
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Total Records", summary.get("total_records", 0))
                        
                        with col2:
                            if "total_products" in summary:
                                st.metric("Products", summary["total_products"])
                            elif "total_categories" in summary:
                                st.metric("Categories", summary["total_categories"])
                        
                        with col3:
                            if "total_value" in summary:
                                st.metric("Total Value", f"${summary['total_value']:,.2f}")
                            elif "total_revenue" in summary:
                                st.metric("Total Revenue", f"${summary['total_revenue']:,.2f}")
                        
                        # Show additional summary details
                        if len(summary) > 3:
                            st.write("**Additional Details:**")
                            for key, value in summary.items():
                                if key not in ["total_records", "total_products", "total_categories", "total_value", "total_revenue"]:
                                    if isinstance(value, float):
                                        value = f"{value:,.2f}"
                                    st.write(f"- **{key.replace('_', ' ').title()}:** {value}")
                        
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

with tab_sql_console:
    st.write("Run your own SQL (SELECT-only) against SQLite.")
    sql_text = st.text_area("SQL", height=160, placeholder='SELECT "Product ID", "Inventory Level" FROM inventory LIMIT 10')
    colc1, colc2 = st.columns([1, 3])
    with colc1:
        run_sql_btn = st.button("Run SQL")
    with colc2:
        st.write("")  # Empty space for alignment

    if run_sql_btn:
        if not sql_text.strip():
            st.warning("Please enter a SQL query.")
        elif not sql_text.strip().lower().startswith("select"):
            st.error("Only SELECT statements are allowed for safety.")
        else:
            try:
                db = get_db(db_path)
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
