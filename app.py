import os
from html import escape
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from agents.orchestrator import OrchestratorAgent
# from agents.viz_agent import render_auto_chart  # Removed - no longer needed
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

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Typography tweak for better readability
st.markdown(
    """
    <style>
    .summary-text { 
        font-size: 15px; 
        line-height: 1.6; 
        font-family: "Segoe UI", Roboto, Arial, sans-serif; 
        white-space: pre-wrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    # Create container for chat messages
    chat_container = st.container()
    
    # Display chat history in the container
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input at the bottom
    if question := st.chat_input("Ask about inventory data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": question})
        
        # Display user message in chat container
        with chat_container:
            with st.chat_message("user"):
                st.markdown(question)
        
        # Process with agent
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
                
                # Display assistant response in chat container
                with chat_container:
                    if not result["success"]:
                        with st.chat_message("assistant"):
                            st.error(f"❌ {result['error']}")
                            # Add error to chat history
                            st.session_state.messages.append({"role": "assistant", "content": f"❌ Error: {result['error']}"})
                    else:
                        # Technical details shown between user and assistant reply
                        with st.expander("⚙️ Technical Details", expanded=False):
                            # Intent Classification
                            if "intent" in result:
                                st.markdown(f"**Intent:** {result['intent']}")
                            
                            # Display SQL
                            st.markdown("**Generated SQL:**")
                            st.code(result["sql"], language="sql")
                            
                            # Display results
                            st.markdown("**Results:**")
                            if "schema_info" in result and result["schema_info"]:
                                st.markdown(result["schema_info"])
                            elif result["data"] is not None:
                                st.dataframe(result["data"], use_container_width=True)
                                st.caption(f"Rows: {len(result['data'])}")

                        # Build response content (no 'Results: X rows' in main reply)
                        response_parts = []
                        
                        # Add natural language summary if available
                        if "response" in result and result["response"]:
                            safe_text = escape(str(result["response"]))
                            response_parts.append(f"<div class='summary-text'>{safe_text}</div>")
                        
                        # Add SQL query
                        if "sql" in result and result["sql"]:
                            response_parts.append(f"**SQL Query:**\n```sql\n{result['sql']}\n```")
                        
                        # Add chart info
                        if "chart" in result and result["chart"]:
                            response_parts.append("📊 **Visualization generated**")
                        
                        # Add report summary
                        if "summary" in result and result["summary"]:
                            summary = result["summary"]
                            summary_text = f"📋 **Report Summary:** {summary.get('total_records', 0)} records"
                            if "total_products" in summary:
                                summary_text += f", {summary['total_products']} products"
                            response_parts.append(summary_text)
                        
                        # Display the response
                        full_response = "\n\n".join(response_parts)
                        # Persist table in chat history so it survives reruns
                        history_suffix = ""
                        if result.get("response_table_md"):
                            history_suffix = "\n\n" + result["response_table_md"]
                        assistant_history_content = full_response + history_suffix
                        with st.chat_message("assistant"):
                            st.markdown(assistant_history_content, unsafe_allow_html=True)
                        
                        # Add to chat history (including table markdown if present)
                        st.session_state.messages.append({"role": "assistant", "content": assistant_history_content})
                        
                        # Display chart if available
                        if "chart" in result and result["chart"]:
                            st.subheader("📊 Visualization")
                            st.pyplot(result["chart"])
                        
                        # Debug info (timings, intent, viz spec)
                        if show_debug and "debug" in result:
                            st.subheader("🔎 Debug Info")
                            st.json(result.get("debug", {}))
                            if "viz_spec" in result and result["viz_spec"]:
                                st.caption("Visualization Spec")
                                st.json(result["viz_spec"])
                        
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
