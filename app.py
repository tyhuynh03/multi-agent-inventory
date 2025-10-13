import os
import time
import json
import pickle
from html import escape
import streamlit as st
import streamlit.components.v1
import pandas as pd
from dotenv import load_dotenv

from agents.orchestrator import OrchestratorAgent
# from agents.viz_agent import render_auto_chart  # Removed - no longer needed
from db.connection import get_db, run_sql_unified
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

# Config flags
LOAD_SAVED_CHARTS = False  # Tạm thời bỏ load chart từ conversation/segments

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load conversation from file if exists
def load_conversation():
    """Load conversation from file"""
    try:
        if os.path.exists("data/conversation.json"):
            with open("data/conversation.json", "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    st.warning("Conversation file is empty")
                    return False
                
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON format in conversation file: {e}")
                    # Try to backup and reset
                    backup_file = f"data/conversation_backup_{int(time.time())}.json"
                    os.rename("data/conversation.json", backup_file)
                    st.info(f"Backed up corrupted file to {backup_file}")
                    return False
                
                st.session_state.messages = data.get("messages", [])

                # Optionally skip loading saved charts
                if LOAD_SAVED_CHARTS:
                    charts = []
                    for chart_data in data.get("charts", []):
                        if "chart_png_base64" in chart_data:
                            try:
                                import base64
                                png_bytes = base64.b64decode(chart_data["chart_png_base64"])
                                charts.append({
                                    "question": chart_data.get("question", ""),
                                    "chart": None,
                                    "chart_png": png_bytes,
                                    "timestamp": chart_data.get("timestamp", time.time())
                                })
                            except Exception as e:
                                st.warning(f"Could not load chart PNG: {e}")
                                continue
                    st.session_state.charts = charts
                    st.success(f"✅ Loaded {len(charts)} charts from conversation")
                else:
                    st.session_state.charts = []
                return True
    except Exception as e:
        st.error(f"Error loading conversation: {e}")
        # Try to backup corrupted file
        if os.path.exists("data/conversation.json"):
            try:
                backup_file = f"data/conversation_backup_{int(time.time())}.json"
                os.rename("data/conversation.json", backup_file)
                st.info(f"Backed up corrupted file to {backup_file}")
            except:
                pass
    return False

def save_conversation():
    """Save conversation to file"""
    try:
        os.makedirs("data", exist_ok=True)
        
        # Convert charts to serializable format (PNG images)
        serializable_charts = []
        for chart_data in st.session_state.get("charts", []):
            if chart_data and "chart_png" in chart_data:
                try:
                    import base64
                    # Convert PNG bytes to base64 string for JSON storage
                    if chart_data["chart_png"]:
                        png_base64 = base64.b64encode(chart_data["chart_png"]).decode('utf-8')
                        serializable_chart = {
                            "question": chart_data.get("question", ""),
                            "chart_png_base64": png_base64,
                            "timestamp": chart_data.get("timestamp", time.time())
                        }
                        serializable_charts.append(serializable_chart)
                except Exception as e:
                    st.warning(f"Could not serialize chart PNG: {e}")
                    continue
        
        data = {
            "messages": st.session_state.messages,
            "charts": serializable_charts,
            "timestamp": time.time()
        }
        with open("data/conversation.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving conversation: {e}")

# Load conversation on startup
if not st.session_state.messages:
    load_conversation()

def save_chat_segment():
    """Save current conversation as a named chat segment"""
    try:
        if not st.session_state.messages:
            st.warning("No conversation to save")
            return
        
        # Create segment data with default name
        segment_name = f"Chat_{int(time.time())}"
        segment_data = {
            "name": segment_name,
            "messages": st.session_state.messages,
            "charts": st.session_state.get("charts", []),
            "timestamp": time.time(),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save to file
        os.makedirs("data/chat_segments", exist_ok=True)
        filename = f"data/chat_segments/{segment_name}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(segment_data, f, ensure_ascii=False, indent=2)
        
        st.success(f"✅ Chat segment '{segment_name}' saved!")
        st.rerun()
    except Exception as e:
        st.error(f"Error saving chat segment: {e}")

def load_chat_segments():
    """Load and display available chat segments"""
    try:
        if not os.path.exists("data/chat_segments"):
            st.info("No chat segments found")
            return
        
        # Get all segment files
        segment_files = [f for f in os.listdir("data/chat_segments") if f.endswith('.json')]
        
        if not segment_files:
            st.info("No chat segments found")
            return
        
        # Display segments
        for i, filename in enumerate(segment_files):
            try:
                with open(f"data/chat_segments/{filename}", "r", encoding="utf-8") as f:
                    segment_data = json.load(f)
                
                # Compact display for sidebar
                with st.expander(f"📁 {segment_data.get('name', filename)}", expanded=False):
                    st.caption(f"Created: {segment_data.get('created_at', 'Unknown')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📂 Load", key=f"load_{i}", use_container_width=True):
                            load_chat_segment(filename)
                    with col2:
                        if st.button("🗑️", key=f"delete_{i}", use_container_width=True):
                            delete_chat_segment(filename)
                
            except Exception as e:
                st.error(f"Error loading segment {filename}: {e}")
                
    except Exception as e:
        st.error(f"Error loading chat segments: {e}")

def load_chat_segment(filename):
    """Load a specific chat segment"""
    try:
        with open(f"data/chat_segments/{filename}", "r", encoding="utf-8") as f:
            segment_data = json.load(f)
        
        # Load messages and charts
        st.session_state.messages = segment_data.get("messages", [])
        st.session_state.charts = segment_data.get("charts", [])
        
        st.success(f"✅ Loaded chat segment: {segment_data.get('name', filename)}")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error loading chat segment: {e}")

def delete_chat_segment(filename):
    """Delete a chat segment"""
    try:
        os.remove(f"data/chat_segments/{filename}")
        st.success(f"✅ Deleted chat segment: {filename}")
        st.rerun()
    except Exception as e:
        st.error(f"Error deleting chat segment: {e}")

# Typography tweak for better readability
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Apply Inter font to specific elements only */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox select,
    .stButton button,
    .stMarkdown,
    .stWrite {
        font-family: 'Inter', sans-serif !important;
    }
    
    .summary-text { 
        font-size: 15px; 
        line-height: 1.6; 
        font-family: 'Inter', sans-serif; 
        white-space: pre-wrap;
    }
    
    /* Fix text input rendering */
    .stTextInput input {
        font-family: 'Inter', sans-serif !important;
        font-size: 16px !important;
        line-height: 1.5 !important;
        letter-spacing: normal !important;
        text-rendering: optimizeLegibility !important;
    }
    
    /* Fix any overlapping text issues */
    .stTextInput input::placeholder {
        font-family: 'Inter', sans-serif !important;
        opacity: 0.6 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🤖 Multi-Agent for Inventory (PostgreSQL + LangChain, Groq)")

# --- Initialize Orchestrator ---
@st.cache_resource
def get_orchestrator():
    return OrchestratorAgent(db_type="postgresql")

with st.sidebar:
    st.header("📚 Chat Segments")
    
    # Load chat segments
    load_chat_segments()
    
    st.divider()
    
    st.header("⚙️ Settings")
    db_type = st.selectbox("Database Type", ["postgresql", "sqlite"], index=0)
    if db_type == "sqlite":
        db_path = st.text_input("SQLite path", value=DEFAULT_DB_PATH)
    else:
        st.info("Using PostgreSQL: localhost:5432/inventory_db")
    
    # Display current model
    st.info(f"🤖 Model: {DEFAULT_MODEL}")
    
    # Hidden settings (use defaults)
    use_semantic_search = True
    examples_path = DEFAULT_EXAMPLES_PATH
    top_k = RAG_TOP_K
    show_debug = False
    
    st.divider()
    
    # Save as chat segment
    segment_name = st.text_input("Segment name:", value="", placeholder="Enter segment name...")
    if st.button("💾 Save as Chat Segment", use_container_width=True):
        if segment_name.strip():
            # Save with custom name
            try:
                if not st.session_state.messages:
                    st.warning("No conversation to save")
                else:
                    segment_data = {
                        "name": segment_name.strip(),
                        "messages": st.session_state.messages,
                        "charts": st.session_state.get("charts", []),
                        "timestamp": time.time(),
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    os.makedirs("data/chat_segments", exist_ok=True)
                    filename = f"data/chat_segments/{segment_name.strip().replace(' ', '_')}.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(segment_data, f, ensure_ascii=False, indent=2)
                    
                    st.success(f"✅ Chat segment '{segment_name.strip()}' saved!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error saving chat segment: {e}")
        else:
            save_chat_segment()
    
    # Button trên
    if st.button("Check DB", use_container_width=True):
        try:
            if db_type == "postgresql":
                # Test PostgreSQL connection
                df, error = run_sql_unified("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'", "postgresql")
                if error:
                    st.error(f"PostgreSQL error: {error}")
                else:
                    st.success("✅ PostgreSQL Connected!")
                    # Get table names
                    df_tables, _ = run_sql_unified("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name", "postgresql")
                    st.write("Tables:")
                    st.code(df_tables['table_name'].tolist(), language="bash")
            else:
                db = get_db(db_path, "sqlite")
                st.success("✅ SQLite Connected. Tables:")
                st.code(db.get_usable_table_names(), language="bash")
        except Exception as e:
            st.error(f"DB error: {e}")
    
    # Button dưới
    if st.button("🔄 Rebuild RAG Index", use_container_width=True):
        try:
            from rag.rag_retriever import get_rag_retriever
            rag_agent = get_rag_retriever()
            result = rag_agent.build_index_from_examples(examples_path, force_rebuild=True)
            if result["success"]:
                st.success(f"✅ Rebuilt RAG index: {result['indexed_count']} examples")
            else:
                st.error(f"❌ Failed: {result['error']}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Tabs: Text-to-SQL and SQL Console
# Keeping a single chat-like flow in Text-to-SQL and show charts under results.
tab_text2sql, tab_sql_console = st.tabs(["Text-to-SQL", "SQL Console"]) 

with tab_text2sql:
    st.write("Enter your question in English. The app will generate a `SELECT` query and run it on PostgreSQL.")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.charts = []
        # Clear conversation file
        if os.path.exists("data/conversation.json"):
            os.remove("data/conversation.json")
        st.rerun()
    
    
    
    # Create container for chat messages
    chat_container = st.container()
    
    # Display chat history in the container
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display chart if this message has a chart
                if "chart_index" in message and "charts" in st.session_state:
                    chart_index = message["chart_index"]
                    if chart_index < len(st.session_state.charts):
                        chart_data = st.session_state.charts[chart_index]
                        if chart_data:
                            st.subheader("📊 Visualization")
                            try:
                                # Try to display as Plotly figure first (for new charts)
                                if "chart" in chart_data and chart_data["chart"] is not None:
                                    st.plotly_chart(chart_data["chart"], use_container_width=True)
                                # Display PNG image (for loaded charts)
                                elif "chart_png" in chart_data and chart_data["chart_png"]:
                                    # Display with better quality and layout preservation
                                    st.image(
                                        chart_data["chart_png"], 
                                        caption=chart_data.get("question", "Chart"), 
                                        use_container_width=True,
                                        channels="RGB"  # Ensure proper color channels
                                    )
                                else:
                                    st.info("📊 Chart was saved but cannot be displayed")
                            except Exception as e:
                                st.error(f"Error displaying chart: {e}")
    
    
    # Chat input at the bottom
    if question := st.chat_input("Ask about inventory data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": question})
        
        # Auto-save conversation
        save_conversation()
        
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
                    db_type="postgresql",
                    use_retriever=use_semantic_search,
                    examples_path=examples_path,
                    top_k=top_k
                )
                
                # Display assistant response in chat container
                with chat_container:
                    if not result["success"]:
                        with st.chat_message("assistant"):
                            st.error(f"❌ {result['error']}")
                            # Technical details for error case
                            with st.expander("⚙️ Technical Details", expanded=False):
                                # Show SQL if available
                                if "sql" in result and result["sql"]:
                                    st.markdown("**Generated SQL:**")
                                    st.code(result["sql"], language="sql")
                                # Optional debug sections
                                if "debug" in result and isinstance(result["debug"], dict):
                                    steps = result["debug"].get("steps") or []
                                    if steps:
                                        with st.expander("Steps", expanded=False):
                                            st.json(steps)
                                    gen = result["debug"].get("sql_generate") or {}
                                    if gen:
                                        model = gen.get("model")
                                        if model:
                                            st.caption(f"Model: {model}")
                                        prompt_full = gen.get("prompt_full")
                                        prompt_snippet = gen.get("prompt_snippet")
                                        raw_response = gen.get("raw_response")
                                        retry = gen.get("retry")
                                        if prompt_full:
                                            with st.expander("Prompt (full)", expanded=False):
                                                st.code(prompt_full, language="markdown")
                                        elif prompt_snippet:
                                            with st.expander("Prompt snippet", expanded=False):
                                                st.code(prompt_snippet, language="markdown")
                                        if raw_response:
                                            with st.expander("LLM raw response", expanded=False):
                                                st.code(raw_response, language="markdown")
                                        if retry:
                                            st.caption("Retried: True")
                            # Add error to chat history
                            st.session_state.messages.append({"role": "assistant", "content": f"❌ Error: {result['error']}"})
                    else:
                        # Technical details shown between user and assistant reply
                        with st.expander("⚙️ Technical Details", expanded=False):
                            # Intent Classification
                            if "intent" in result:
                                st.markdown(f"**Intent:** {result['intent']}")
                            
                            # Display SQL (if available)
                            if "sql" in result and result["sql"]:
                                st.markdown("**Generated SQL:**")
                                st.code(result["sql"], language="sql")
                            elif result.get("intent") == "inventory_analytics":
                                st.markdown("**Analytics Type:**")
                                st.info(f"📊 {result.get('analytics_type', 'general_analytics')}")
                            
                            # Optional debug sections (wrapped in nested expanders)
                            if "debug" in result and isinstance(result["debug"], dict):
                                steps = result["debug"].get("steps") or []
                                if steps:
                                    with st.expander("Steps", expanded=False):
                                        st.json(steps)

                                gen = result["debug"].get("sql_generate") or {}
                                if gen:
                                    model = gen.get("model")
                                    if model:
                                        st.caption(f"Model: {model}")
                                    prompt_full = gen.get("prompt_full")
                                    prompt_snippet = gen.get("prompt_snippet")
                                    raw_response = gen.get("raw_response")
                                    retry = gen.get("retry")
                                    if prompt_full:
                                        with st.expander("Prompt (full)", expanded=False):
                                            st.code(prompt_full, language="markdown")
                                    elif prompt_snippet:
                                        with st.expander("Prompt snippet", expanded=False):
                                            st.code(prompt_snippet, language="markdown")
                                    if raw_response:
                                        with st.expander("LLM raw response", expanded=False):
                                            st.code(raw_response, language="markdown")
                                    if retry:
                                        st.caption("Retried: True")

                            
                            # Display results
                            st.markdown("**Results:**")
                            if "schema_info" in result and result["schema_info"]:
                                st.markdown(result["schema_info"])
                            elif result["data"] is not None:
                                st.dataframe(result["data"], use_container_width=True)
                                st.caption(f"Rows: {len(result['data'])}")

                        # Build response content (no markdown table, only Query Results table)
                        response_parts = []
                        
                        # Add natural language summary if available
                        if "response" in result and result["response"]:
                            safe_text = escape(str(result["response"]))
                            response_parts.append(f"<div class='summary-text'>{safe_text}</div>")
                        
                        # Add SQL query (if available)
                        if "sql" in result and result["sql"]:
                            response_parts.append(f"**SQL Query:**\n```sql\n{result['sql']}\n```")
                        
                        # Add analytics info
                        if result.get("intent") == "inventory_analytics" and result.get("analytics_type"):
                            analytics_type = result.get("analytics_type", "").replace("_", " ").title()
                            response_parts.append(f"📊 **Analytics Type:** {analytics_type}")
                        
                        # Add report summary
                        if "summary" in result and result["summary"]:
                            summary = result["summary"]
                            summary_text = f"📋 **Report Summary:** {summary.get('total_records', 0)} records"
                            if "total_products" in summary:
                                summary_text += f", {summary['total_products']} products"
                            response_parts.append(summary_text)
                        
                        # Display response content (no markdown table)
                        full_response = "\n\n".join(response_parts)
                        assistant_history_content = full_response  # No response_table_md
                        with st.chat_message("assistant"):
                            st.markdown(assistant_history_content, unsafe_allow_html=True)
                            
                            # Display main data table in chat (skip for visualize intent)
                            if result["data"] is not None and not result["data"].empty and result.get("intent") != "visualize":
                                st.markdown("**📊 Query Results:**")
                                st.dataframe(result["data"], use_container_width=True)
                                st.caption(f"📈 Total rows: {len(result['data'])}")
                        
                        # Prepare message content
                        message_content = {"role": "assistant", "content": assistant_history_content}
                        
                        # Display chart if available
                        if "chart" in result and result["chart"]:
                            st.subheader("📊 Visualization")
                            try:
                                import plotly.graph_objects as go
                                import plotly.io as pio
                                from streamlit import plotly_chart
                                st.plotly_chart(result["chart"], use_container_width=True)
                                
                                # Save chart as PNG for persistence
                                if "charts" not in st.session_state:
                                    st.session_state.charts = []
                                chart_index = len(st.session_state.charts)
                                
                                # Use Plotly's built-in download functionality for PNG
                                try:
                                    import plotly.io as pio
                                    # Use the same method as Plotly's download button
                                    png_bytes = pio.to_image(
                                        result["chart"], 
                                        format="png",
                                        width=800,  # Fixed width for consistency
                                        height=600, # Fixed height for consistency
                                        scale=1,    # Use default scale like download button
                                        engine="kaleido"
                                    )
                                    chart_png = png_bytes
                                except ImportError:
                                    st.info("📊 Chart displayed successfully. Install 'kaleido' for PNG export.")
                                    chart_png = None
                                except Exception as e:
                                    # More specific error handling
                                    if "kaleido" in str(e).lower():
                                        st.info("📊 Chart displayed successfully. Run: pip install kaleido")
                                    else:
                                        st.warning(f"Chart PNG export failed: {str(e)[:100]}")
                                    chart_png = None
                                
                                st.session_state.charts.append({
                                    "question": question,
                                    "chart": result["chart"],  # Keep original for display
                                    "chart_png": chart_png,   # PNG bytes for persistence
                                    "timestamp": time.time()
                                })
                                
                                # Add chart index to message
                                message_content["chart_index"] = chart_index
                                
                            except Exception:
                                st.pyplot(result["chart"])  # fallback matplotlib
                        
                        # Add to chat history
                        st.session_state.messages.append(message_content)
                        
                        # Auto-save conversation
                        save_conversation()
                        
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
    st.write("Run your own SQL (SELECT-only) against PostgreSQL.")
    sql_text = st.text_area("SQL", height=160, placeholder='SELECT sku_id, current_inventory_quantity FROM inventory LIMIT 10')
    colc1, colc2 = st.columns([1, 3])
    with colc1:
        run_sql_btn = st.button("Run SQL")
    with colc2:
        st.write("")  # Empty space for alignment

    if run_sql_btn:
        if not sql_text.strip():
            st.warning("Please enter a SQL query.")
        elif not (sql_text.strip().lower().startswith("select") or sql_text.strip().lower().startswith("with")):
            st.error("Only SELECT statements are allowed for safety.")
        else:
            try:
                # Use the selected database type
                current_db_type = db_type if 'db_type' in locals() else "postgresql"
                df, err = run_sql_unified(sql_text, current_db_type)
                if err:
                    st.error(err)
                else:
                    st.subheader("Results")
                    st.code(sql_text, language="sql")
                    
                    st.dataframe(df, use_container_width=True)
                    st.caption(f"Rows: {len(df)}")
            except Exception as e:
                st.error(str(e))
