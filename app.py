# Ban đầu là 10:37 ngày 11/12/2025
import os
import time
import datetime
import json
import pickle
import re
import textwrap
import base64
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

# Page icon (Streamlit logo) -> use Logo_RG.png if available
logo_rg_path = os.path.abspath("assets/logo_rg.png")
page_icon_path = logo_rg_path if os.path.exists(logo_rg_path) else None

st.set_page_config(page_title="Multi-Agent for Inventory", layout="wide", page_icon=page_icon_path)

# Config flags
# Bật load chart đã lưu để khi refresh vẫn hiển thị chart
LOAD_SAVED_CHARTS = True

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "selected_segment" not in st.session_state:
    st.session_state.selected_segment = None

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
                        try:
                            import plotly.io as pio
                            chart_obj = None
                            if "chart_json" in chart_data:
                                try:
                                    chart_obj = pio.from_json(chart_data["chart_json"])
                                except Exception as e:
                                    st.warning(f"Could not load chart JSON: {e}")
                            charts.append({
                                "question": chart_data.get("question", ""),
                                "chart": chart_obj,
                                "chart_png": None,
                                "timestamp": chart_data.get("timestamp", time.time())
                            })
                        except Exception as e:
                            st.warning(f"Could not load chart: {e}")
                            continue
                    st.session_state.charts = charts
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
            if chart_data:
                try:
                    import plotly.io as pio
                    serializable_chart = {
                        "question": chart_data.get("question", ""),
                        "timestamp": chart_data.get("timestamp", time.time())
                    }
                    # Lưu JSON của plotly figure (ưu tiên)
                    if chart_data.get("chart") is not None:
                        try:
                            serializable_chart["chart_json"] = pio.to_json(chart_data["chart"])
                        except Exception as e:
                            st.warning(f"Could not serialize chart JSON: {e}")
                    serializable_charts.append(serializable_chart)
                except Exception as e:
                    st.warning(f"Could not serialize chart: {e}")
                    continue
        
        data = {
            "messages": st.session_state.messages,
            "charts": serializable_charts,
            "timestamp": time.time()
        }
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (pd.Timestamp, datetime.date, datetime.datetime)):
                    return obj.isoformat()
                return super().default(obj)

        with open("data/conversation.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
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
    """Load and display available chat segments (History)"""
    try:
        if not os.path.exists("data/chat_segments"):
            st.markdown("""
            <div class="instruction-box">
                <p style="margin: 0; font-size: 14px;"><strong>No history yet</strong><br>Saved chats will appear here.</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Get all segment files
        segment_files = [f for f in os.listdir("data/chat_segments") if f.endswith('.json')]
        # Sort by modification time (newest first)
        segment_files.sort(key=lambda x: os.path.getmtime(os.path.join("data/chat_segments", x)), reverse=True)
        
        if not segment_files:
            st.markdown("""
            <div class="instruction-box">
                <p style="margin: 0; font-size: 14px;"><strong>No history yet</strong><br>Saved chats will appear here.</p>
            </div>
            """, unsafe_allow_html=True)
            return
        
        if "editing_segment" not in st.session_state:
            st.session_state.editing_segment = None

        for i, filename in enumerate(segment_files):
            try:
                with open(f"data/chat_segments/{filename}", "r", encoding="utf-8") as f:
                    segment_data = json.load(f)
                
                segment_name = segment_data.get('name', filename.replace('.json', ''))
                is_selected = st.session_state.get("selected_segment") == filename
                
                # Check directly if this specific file is being edited
                is_editing = st.session_state.editing_segment == filename
                
                if is_editing:
                    # EDIT MODE ROW
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        new_name = st.text_input("Rename", value=segment_name, key=f"edit_input_{i}", label_visibility="collapsed")
                    with c2:
                        # Save (Green Check) or Cancel (Red X)
                        if st.button("💾", key=f"save_edit_{i}", use_container_width=True):
                            rename_chat_segment(filename, new_name)
                        
                else:
                    # NORMAL MODE ROW
                    # Use columns to mimic the layout: [Name Button (flexible)] [Edit] [Delete]
                    # Note: We use a larger ratio for the name to push icons to the right
                    
                    # Custom styling for active row
                    active_css = ""
                    if is_selected:
                        # We can't style st.columns directly easily, but we can style the buttons using 'key' if needed
                        # or just rely on the segment-item wrapper if we were using it.
                        # For now, we use standard buttons but maybe add an indicator.
                        pass

                    cols = st.columns([0.7, 0.15, 0.15])
                    with cols[0]:
                        # Main Name Button
                        label = f"🔹 {segment_name}" if is_selected else segment_name
                        if st.button(label, key=f"seg_btn_{i}", use_container_width=True):
                            st.session_state.selected_segment = filename
                            load_chat_segment(filename)
                    with cols[1]:
                        if st.button("✏️", key=f"edit_btn_{i}", use_container_width=True):
                            st.session_state.editing_segment = filename
                            st.rerun()
                    with cols[2]:
                        if st.button("🗑️", key=f"del_btn_{i}", use_container_width=True):
                            delete_chat_segment(filename)
                
            except Exception as e:
                continue
                
    except Exception as e:
        st.error(f"History error: {e}")

def load_chat_segment(filename):
    """Load a specific chat segment"""
    try:
        with open(f"data/chat_segments/{filename}", "r", encoding="utf-8") as f:
            segment_data = json.load(f)
        
        # Load messages and charts (rehydrate plotly figures from JSON)
        st.session_state.messages = segment_data.get("messages", [])
        charts_loaded = []
        for chart_item in segment_data.get("charts", []):
            chart_obj = None
            try:
                import plotly.io as pio
                if chart_item.get("chart_json"):
                    chart_obj = pio.from_json(chart_item["chart_json"])
            except Exception as e:
                st.warning(f"Could not load chart from segment: {e}")
            charts_loaded.append({
                "question": chart_item.get("question", ""),
                "chart": chart_obj,
                "chart_png": None,
                "chart_json": chart_item.get("chart_json"),
                "timestamp": chart_item.get("timestamp", time.time())
            })
        st.session_state.charts = charts_loaded
        
        st.session_state.selected_segment = filename
        st.success(f"✅ Loaded chat segment: {segment_data.get('name', filename)}")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error loading chat segment: {e}")

def delete_chat_segment(filename):
    """Delete a chat segment"""
    try:
        os.remove(f"data/chat_segments/{filename}")
        st.toast(f"✅ Deleted: {filename}", icon="🗑️")
        time.sleep(1) # Visual delay before reload
        st.rerun()
    except Exception as e:
        st.error(f"Error deleting chat segment: {e}")

def rename_chat_segment(filename, new_name):
    """Rename a chat segment"""
    try:
        # Read current segment data
        with open(f"data/chat_segments/{filename}", "r", encoding="utf-8") as f:
            segment_data = json.load(f)
        
        # Update name
        clean_name = new_name.strip()
        if not clean_name:
            st.warning("Name cannot be empty")
            return

        segment_data["name"] = clean_name
        
        # Create new filename
        new_filename = f"{clean_name.replace(' ', '_')}.json"
        new_filepath = f"data/chat_segments/{new_filename}"
        
        # Save with new name
        with open(new_filepath, "w", encoding="utf-8") as f:
            json.dump(segment_data, f, ensure_ascii=False, indent=2)
        
        # Delete old file if filename changed
        if filename != new_filename:
            os.remove(f"data/chat_segments/{filename}")
        
        # Clear editing state
        st.session_state.editing_segment = None
        st.toast(f"✅ Renamed to '{clean_name}'", icon="✏️")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Error renaming chat segment: {e}")

        
def markdown_to_html(text: str) -> str:
    """Convert markdown to HTML, fallback with basic replacements."""
    if text is None:
        return ""
    try:
        import markdown as md
        return md.markdown(str(text), extensions=["extra", "sane_lists"])
    except Exception:
        escaped = escape(str(text))
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?m)^- (.+)$", r"<ul><li>\1</li></ul>", escaped)
        return escaped.replace("\n", "<br>")


def sanitize_html(raw: str) -> str:
    """Escape script/style tags to prevent rendering."""
    if raw is None:
        return ""
    cleaned = re.sub(
        r"<\s*(script|style)(.|\n)*?<\s*/\s*\1\s*>",
        lambda m: escape(m.group(0)),
        str(raw),
        flags=re.IGNORECASE,
    )
    return cleaned


def get_sql_text(obj: dict) -> str:
    """Extract SQL text from result/message with multiple possible keys."""
    if not obj or not isinstance(obj, dict):
        return None
    for key in ("sql", "generated_sql", "sql_query", "query_sql"):
        val = obj.get(key)
        if val:
            return str(val)
    return None


st.markdown(textwrap.dedent("""
<style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --primary-color: #4F46E5; /* Indigo 600 */
        --primary-light: #818CF8;
        --secondary-color: #10B981; /* Emerald 500 */
        --bg-color: #F9FAFB;      /* Gray 50 */
        --surface-color: #FFFFFF;
        --text-primary: #111827;  /* Gray 900 */
        --text-secondary: #4B5563; /* Gray 600 */
        --border-color: #E5E7EB;  /* Gray 200 */
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    /* DARK THEME OVERRIDES - applied to Streamlit app container */
    [data-testid="stAppViewContainer"].dark-theme {
        --primary-color: #6366F1; /* Indigo 500 */
        --bg-color: #0F172A;      /* Slate 900 */
        --surface-color: #1E293B; /* Slate 800 */
        --text-primary: #F3F4F6;  /* Gray 100 */
        --text-secondary: #9CA3AF; /* Gray 400 */
        --border-color: #334155;  /* Slate 700 */
    }

    /* BASE STYLES */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-primary) !important;
        background-color: var(--bg-color) !important;
    }
    body, [data-testid="stAppViewContainer"] .main {
        font-size: 14.5px;
        line-height: 1.5;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    /* Form controls - slightly smaller */
    input, textarea, button, select, label, .stMarkdown, .stTextInput, .stTextArea {
        font-size: 14px !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em !important;
    }

    /* SIDEBAR STYLING */
    [data-testid="stSidebar"] {
        background-color: var(--surface-color) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    /* Ensure sidebar content background matches */
    [data-testid="stSidebar"] > div {
        background-color: var(--surface-color) !important;
    }
    
    /* Dark Theme Sidebar Overrides */
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"],
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] > div {
        background-color: var(--primary-color) !important; /* Blue Water like User Bubble */
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Ensure Text Contrast on Blue Sidebar */
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] h1,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] h2,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] h3,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] span,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] div,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] p,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] label,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] input {
        color: #FFFFFF !important;
    }
    
    /* Dark Mode Sidebar Buttons: Semi-transparent white to look good on blue */
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] .stButton button {
        background-color: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: #FFFFFF !important;
    }
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] .stButton button:hover {
        background-color: rgba(255, 255, 255, 0.3) !important;
        border-color: #FFFFFF !important;
    }

    /* GLOBAL SIDEBAR TYPOGRAPHY - BIGGER & BOLDER */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] div, 
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox label {
        font-size: 15px !important;
        font-weight: 600 !important; /* Bolder text as requested */
    }
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        font-size: 18px !important;
        font-weight: 800 !important; /* Very bold headers */
        letter-spacing: 0.5px !important;
    }
    
    /* Make Settings Section Bold */
    [data-testid="stSidebar"] h4 {
        font-weight: 700 !important;
        font-size: 14px !important;
        color: var(--text-primary) !important;
    }
    /* Sidebar Buttons (History Items) */
    [data-testid="stSidebar"] .stButton button p {
        font-size: 15px !important;
        font-weight: 600 !important;
    }

    /* Sidebar Headers */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 13px !important; /* Slightly larger for uppercase label */
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
    }

    /* REDUCE TOP SPACING */
    .block-container {
        padding-top: 1.5rem !important;
    }

    
    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Custom "New Segment" Button Style */
    div.stButton > button[key="new_segment_btn"] {
        background: linear-gradient(135deg, var(--primary-color), var(--primary-light)) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-md) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button[key="new_segment_btn"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 12px rgba(79, 70, 229, 0.2) !important;
    }
    
    /* Segment Items in Sidebar */
    .segment-item {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.15s ease;
        color: var(--text-secondary);
        font-size: 0.9rem;
    }
    .segment-item:hover {
        background-color: var(--bg-color);
        color: var(--primary-color);
    }
    .segment-item.active {
        background-color: #EEF2FF; /* Indigo 50 */
        color: var(--primary-color);
        font-weight: 500;
        border-left: 3px solid var(--primary-color);
    }
    
    /* CUSTOM TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        padding-bottom: 4px;
        border-bottom: 2px solid var(--border-color);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 8px 16px;
        border-radius: 6px 6px 0 0;
        border: none;
        background-color: transparent;
        color: var(--text-secondary);
        font-weight: 500;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: transparent;
        color: var(--primary-color);
        border-bottom: 2px solid var(--primary-color);
        margin-bottom: -2px; /* Pull down to overlay border */
    }

    /* CARDS */
    .card-item {
        background-color: var(--surface-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        transition: all 0.2s ease !important;
        box-shadow: var(--shadow-sm) !important;
    }
    /* Dark Theme Card Override */
    [data-testid="stAppViewContainer"].dark-theme .card-item {
        background-color: #1E293B !important; /* Force Slate 800 */
        border-color: #334155 !important;
        color: #F3F4F6 !important;
    }
    [data-testid="stAppViewContainer"].dark-theme .card-item h4 {
        color: #F3F4F6 !important;
    }
    [data-testid="stAppViewContainer"].dark-theme .card-item p {
        color: #9CA3AF !important;
    }
    
    .card-item:hover {
        border-color: var(--primary-color) !important;
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* CHAT INTERFACE - BUBBLES */
    .chat-row {
        display: flex;
        gap: 12px;
        margin-bottom: 20px;
        width: 100%;
        align-items: center; /* Vertically center avatar with bubble */
    }
    
    /* User Message */
    .chat-row.user {
        flex-direction: row;
        justify-content: flex-end;
    }
    .chat-bubble.user {
        background: var(--primary-color);
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 16px;
        box-shadow: var(--shadow-md);
        max-width: 60%;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .chat-avatar.user {
        width: 32px; height: 32px;
        background: var(--primary-color);
        color: white;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold;
        font-size: 0.8rem;
    }
    
    /* Assistant Message */
    .chat-row.assistant {
        flex-direction: row;
    }
    .chat-bubble.assistant {
        background: var(--surface-color);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 18px 18px 18px 4px;
        padding: 14px 20px;
        box-shadow: var(--shadow-sm);
        max-width: 75%;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .chat-icon.assistant {
        width: 32px; height: 32px;
        background: #E0E7FF; /* Indigo 100 */
        color: var(--primary-color);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem;
    }

    /* CODE BLOCKS Customization */
    code {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85em;
        background-color: #F1F5F9; /* Slate 100 */
        color: #B91C1C; /* Red 700 */
        padding: 2px 4px;
        border-radius: 4px;
    }
    pre {
        background-color: #1E293B !important; /* Slate 800 */
        color: #E2E8F0 !important; /* Slate 200 */
        border-radius: 8px !important;
        padding: 12px !important;
    }

    /* Fix Chat Input Bottom Position & Input Styling */
    /* Sidebar Settings Inputs - Add Borders */
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
    [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {
        border: 1px solid #E5E7EB !important;
        border-radius: 8px !important;
        background-color: #FFFFFF !important;
    }
    /* Dark mode override */
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {
        border-color: #334155 !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }

    div[data-testid="stChatInput"] {
        backdrop-filter: blur(8px);
        background: rgba(255, 255, 255, 0.1); /* Glass effect base */
    }
    div[data-testid="stChatInput"] > div {
        border-color: var(--primary-color) !important;
        border-radius: 24px !important; /* Pill shape input */
        background-color: var(--surface-color) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
    }
    div[data-testid="stChatInput"] textarea {
        font-size: 1rem !important;
        padding-left: 0.5rem !important; /* Remove excess padding */
    }

    /* SETTINGS POPOVER */
    [data-testid="stSidebar"] [data-testid="stPopover"] > button {
        background-color: transparent !important;
        border: 1px dashed var(--border-color) !important;
        color: var(--text-secondary) !important;
        width: 100%;
    }
    [data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
        background-color: #EEF2FF !important;
    }

    /* DARK MODE SPECIFICS */
    [data-testid="stAppViewContainer"].dark-theme .chat-bubble.assistant {
        background: #1E293B !important; /* Slate 800 */
        border-color: #334155 !important;
        color: #F3F4F6 !important;
    }
    [data-testid="stAppViewContainer"].dark-theme .chat-bubble.assistant strong,
    [data-testid="stAppViewContainer"].dark-theme .chat-bubble.assistant p {
        color: #F3F4F6 !important;
    }
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stChatInput"] > div {
        background-color: #1E293B !important;
        border-color: #4F46E5 !important;
    }
    [data-testid="stAppViewContainer"].dark-theme textarea {
        color: #F3F4F6 !important;
        background-color: #1E293B !important;
    }

    /* Force Sidebar Darker in Dark Mode */
    /* Force Sidebar Darker in Dark Mode */
    /* Force Sidebar Darker in Dark Mode */
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"],
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] > div {
        background-color: var(--primary-color) !important; /* Match User Bubble */
    }
    
    /* Sticky Bottom Settings Logic */
    /* Use position: sticky to keep it visible at bottom of scrollable sidebar */
    [data-testid="stSidebar"] .element-container:has(.settings-bottom) {
        position: sticky !important;
        bottom: 0 !important;
        z-index: 999 !important;
        background-color: var(--surface-color) !important;
        padding-bottom: 24px !important;
        margin-bottom: 0 !important;
        border-top: 1px solid var(--border-color) !important;
    }
    /* Ensure dark mode background matches */
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] .element-container:has(.settings-bottom) {
        background-color: var(--primary-color) !important; /* Match Sidebar Blue */
    }

    /* Fixed Sidebar Button Alignment (Center Icons) */
    [data-testid="stSidebar"] .stButton button {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        line-height: 1 !important;
        min-height: 44px !important; /* Match text input height */
    }
    
    /* Segment Active State Dark Mode */
    [data-testid="stAppViewContainer"].dark-theme .segment-item.active {
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: #FFFFFF !important;
        border-left-color: #FFFFFF !important;
    }

    /* Make Segment Input BOLD */
    [data-testid="stSidebar"] input[aria-label="Segment name:"] {
        border: 2px solid var(--primary-color) !important;
        background-color: var(--bg-color) !important;
        font-weight: 500 !important;
    }
    [data-testid="stAppViewContainer"].dark-theme [data-testid="stSidebar"] input[aria-label="Segment name:"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        color: #fff !important;
    }

    /* Hide "Press Enter to apply" text in Sidebar Input */
    [data-testid="stSidebar"] [data-testid="InputInstructions"] {
        display: none !important;
    }

</style>

"""), unsafe_allow_html=True)

# JS chỉnh width input theo trạng thái sidebar
st.markdown(textwrap.dedent("""
<script>
(function() {
    function adjustChatInputWidth() {
        const chatInput = document.querySelector('div[data-testid="stChatInput"]');
        if (!chatInput) {
            setTimeout(adjustChatInputWidth, 100);
            return;
        }
        
        // Target the main content block to match its width and position
        const mainBlock = document.querySelector('.main .block-container');
        
        if (mainBlock) {
            const rect = mainBlock.getBoundingClientRect();
            
            // Exact sync with main content
            chatInput.style.left = rect.left + 'px';
            chatInput.style.width = rect.width + 'px';
            chatInput.style.bottom = '0px'; /* Lowered to bottom */
            chatInput.style.marginBottom = '12px'; /* Add slight spacing from very edge */
        }
    }

    // Run on load and resize
    adjustChatInputWidth();
    window.addEventListener('resize', adjustChatInputWidth);

    // Continuous check loop (robust against sidebar toggles and dynamic content)
    setInterval(adjustChatInputWidth, 200);

    // Also observe DOM changes just in case
    const observer = new MutationObserver(adjustChatInputWidth);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
})();
</script>
"""), unsafe_allow_html=True)



# Logo paths
logo_cntt_path = os.path.abspath("assets/logo.png")

# Overlay logo RG (shows when sidebar collapsed via JS)
logo_rg_b64 = None
if os.path.exists(logo_rg_path):
    with open(logo_rg_path, "rb") as f:
        logo_rg_b64 = base64.b64encode(f.read()).decode("utf-8")
    st.markdown(
        f"""
        <div id="logo-rg-container" style="display:none; position:fixed; top:16px; left:16px; z-index:1001;">
            <img src="data:image/png;base64,{logo_rg_b64}" style="width:140px;">
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Initialize Orchestrator ---
@st.cache_resource
def get_orchestrator():
    return OrchestratorAgent(db_type="postgresql")

# Sidebar 
with st.sidebar:

    #  Logo Logo_CNTT.png sau header
    if os.path.exists(logo_cntt_path):
        st.markdown("<div style='padding: 0 20px; margin: 16px 0;'>", unsafe_allow_html=True)
        st.image(logo_cntt_path, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Save Segment functionality at TOP
    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
    col_seg_input, col_seg_save = st.columns([3, 1])
    with col_seg_input:
        segment_name = st.text_input("Segment name:", value="", placeholder="Current Chat Name...", key="save_segment_input", label_visibility="collapsed")
    with col_seg_save:
        is_saved = st.button("💾", key="save_segment_btn", use_container_width=True, help="Save Current Chat")
    
    if is_saved:
        if segment_name.strip():
            # Save with custom name
            try:
                if not st.session_state.messages:
                    st.warning("No conversation to save")
                else:
                    # Serialize charts
                    serializable_charts = []
                    for chart_data in st.session_state.get("charts", []):
                        try:
                            import plotly.io as pio
                            chart_json = chart_data.get("chart_json")
                            if not chart_json and chart_data.get("chart") is not None:
                                chart_json = pio.to_json(chart_data["chart"])
                            serializable_charts.append({
                                "question": chart_data.get("question", ""),
                                "chart_json": chart_json,
                                "timestamp": chart_data.get("timestamp", time.time())
                            })
                        except Exception as e:
                            continue

                    segment_data = {
                        "name": segment_name.strip(),
                        "messages": st.session_state.messages,
                        "charts": serializable_charts,
                        "timestamp": time.time(),
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    os.makedirs("data/chat_segments", exist_ok=True)
                    filename = f"data/chat_segments/{segment_name.strip().replace(' ', '_')}.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(segment_data, f, ensure_ascii=False, indent=2)
                    
                    st.toast(f"✅ Saved '{segment_name.strip()}'", icon="💾")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")
        else:
            save_chat_segment()

    #  New Segment button
    st.markdown("<div style='margin: 16px 0 16px 0;'>", unsafe_allow_html=True)
    if st.button("➕ New Segment", width="stretch", key="new_segment_btn", use_container_width=True):
        st.session_state.messages = []
        st.session_state.charts = []
        st.session_state.selected_segment = None # Start fresh
        st.session_state.editing_segment = None
        
        # Clear conversation file for complete reset
        if os.path.exists("data/conversation.json"):
            try:
                os.remove("data/conversation.json")
            except:
                pass
        
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='margin: 20px 0; border-top: 1px solid #e5e7eb;'></div>", unsafe_allow_html=True)
    
    # HISTORY Header
    st.markdown("<h3 style='font-size: 11px; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;'>HISTORY</h3>", unsafe_allow_html=True)
    # Logic handled above, removing duplicate block
    pass
    
    # Load chat segments (displayed as list items với highlight khi selected)
    load_chat_segments()
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Settings ở cuối sidebar với gap từ bottom (Sticky)
    st.markdown("<div class='settings-bottom' style='padding-top: 12px;'>", unsafe_allow_html=True)
    
    # Settings dropdown/popover
    # Settings Area (Always Visible)
    st.markdown("<h3 style='font-size: 12px; font-weight: 600; color: #374151; text-transform: uppercase; margin-bottom: 16px;'>Settings</h3>", unsafe_allow_html=True)
    
    # DATABASE Section
    st.markdown("<h4 style='font-size: 11px; font-weight: 600; color: #374151; text-transform: uppercase; margin: 16px 0 8px 0;'>DATABASE</h4>", unsafe_allow_html=True)
    db_type = st.selectbox("Type", ["PostgreSQL", "SQLite"], index=0, key="db_type_direct", label_visibility="collapsed")
    db_type_lower = "postgresql" if db_type == "PostgreSQL" else "sqlite"
    st.session_state.db_type = db_type_lower
    
    if db_type_lower == "sqlite":
        db_path = st.text_input("Connection", value=DEFAULT_DB_PATH, key="db_path_direct", label_visibility="collapsed")
    else:
        db_connection = st.text_input("Connection", value="localhost:5432/inventory_db", key="db_connection_direct", label_visibility="collapsed")
    
    # Display current model
    st.info(f"🤖 Model: {DEFAULT_MODEL}")
    
    if st.button("Check DB", width="stretch", key="check_db_direct", use_container_width=True):
        try:
            if db_type_lower == "postgresql":
                # Assuming simple check for now, can expand later
                df, error = run_sql_unified("SELECT 1", "postgresql") 
                if error:
                    st.toast(f"❌ PostgreSQL error: {error}")
                else:
                    st.toast("✅ Connected to PostgreSQL", icon="🐘")
            else:
                st.toast("✅ SQLite Connection OK", icon="🗄️")
        except Exception as e:
            st.toast(f"❌ DB Check Error: {e}")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Hidden settings (use defaults) - di chuyển ra ngoài sidebar
use_semantic_search = True
examples_path = DEFAULT_EXAMPLES_PATH
top_k = RAG_TOP_K
show_debug = False

# Get db_type from session state hoặc default
db_type = st.session_state.get("db_type", "postgresql")

# Áp dụng wide_mode và theme từ session state
wide_mode = st.session_state.get("wide_mode", "No")
theme = st.session_state.get("theme", "Light")

# Thêm class vào app container để áp dụng CSS (Streamlit uses a container element)
# Try to add to stAppViewContainer; fallback to body if not found
if wide_mode == "Yes":
    st.markdown("""
    <script>
    (function() {
        var container = document.querySelector('[data-testid="stAppViewContainer"]');
        if (container) {
            container.classList.add('wide-mode');
        } else {
            document.body.classList.add('wide-mode');
        }
    })();
    </script>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <script>
    (function() {
        var container = document.querySelector('[data-testid="stAppViewContainer"]');
        if (container) {
            container.classList.remove('wide-mode');
        } else {
            document.body.classList.remove('wide-mode');
        }
    })();
    </script>
    """, unsafe_allow_html=True)

if theme == "Dark":
    st.markdown("""
    <script>
    (function() {
        var container = document.querySelector('[data-testid="stAppViewContainer"]');
        if (container) {
            container.classList.add('dark-theme');
        } else {
            document.body.classList.add('dark-theme');
        }
    })();
    </script>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <script>
    (function() {
        var container = document.querySelector('[data-testid="stAppViewContainer"]');
        if (container) {
            container.classList.remove('dark-theme');
        } else {
            document.body.classList.remove('dark-theme');
        }
    })();
    </script>
    """, unsafe_allow_html=True)

# Style Main Content - Beautiful Title
st.markdown("""
<div style="text-align: center; padding: 0px 24px 20px 24px;">
    <h1 style="font-size: 42px; font-weight: 800; margin: 0; color: var(--text-primary); letter-spacing: -0.03em;">
        Multi-Agent for <span style="color: var(--primary-color);">Inventory</span>
    </h1>
    <p style="color: var(--text-secondary); margin-top: 12px; font-size: 18px;">Intelligent inventory analytics powered by AI agents</p>
</div>
""", unsafe_allow_html=True)

# Tabs: AI Assisted và SQL Console
tab_text2sql, tab_sql_console = st.tabs(["AI Assisted", "SQL Console"])


with tab_text2sql:
    #  Style: Instruction box replaced by clean alert
    st.markdown("""
    <div style="background-color: #EEF2FF; border-left: 4px solid var(--primary-color); padding: 16px; border-radius: 0 4px 4px 0; margin-bottom: 24px;">
        <p style="margin: 0; color: var(--text-secondary); font-size: 15px;">
            <strong>AI Assisted:</strong> Ask questions in English to generate SQL queries.
            <br><em>Example: "How many products are in stock?"</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <style>
    /* Đảm bảo 3 cards đều nhau và căn giữa */
    .cards-container {
        display: flex !important;
        justify-content: space-between !important; 
        gap: 16px !important;
        margin: 20px 0 8px 0 !important; /* Reduced bottom margin */
        width: 100% !important;
    }
    .card-item {
        flex: 1 1 0 !important;
        /* Removed rigid min-width to prevent overflow */
        min-width: 0 !important; 
        height: 110px !important; /* Fixed Uniform Height */
    } 
    /* NATIVE BUTTON STYLING for Top Cards */
    
    /* Target buttons in the first 3 columns of the main area */
    .main [data-testid="column"]:nth-of-type(1) .stLinkButton a,
    .main [data-testid="column"]:nth-of-type(2) .stButton button,
    .main [data-testid="column"]:nth-of-type(3) .stButton button {
        height: 110px !important;
        width: 100% !important;
        white-space: pre-wrap !important; /* Enable multiline text */
        line-height: 1.5 !important;
        text-align: center !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        
        background-color: var(--surface-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        box-shadow: var(--shadow-sm) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        padding: 8px !important;
    }

    /* Hover effects */
    .main [data-testid="column"]:nth-of-type(1) .stLinkButton a:hover,
    .main [data-testid="column"]:nth-of-type(2) .stButton button:hover,
    .main [data-testid="column"]:nth-of-type(3) .stButton button:hover {
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* Dark Mode specific overrides */
    [data-testid="stAppViewContainer"].dark-theme .main [data-testid="column"]:nth-of-type(1) .stLinkButton a,
    [data-testid="stAppViewContainer"].dark-theme .main [data-testid="column"]:nth-of-type(2) .stButton button,
    [data-testid="stAppViewContainer"].dark-theme .main [data-testid="column"]:nth-of-type(3) .stButton button {
        background-color: #1E293B !important;
        border-color: #334155 !important;
        color: #F3F4F6 !important;
    }
    
    </style>
    <div class="cards-container">
    """, unsafe_allow_html=True)
    # Use standard gap="medium" or "small" to avoid forcing too much space
    col_doc, col_db, col_config = st.columns(3, gap="small")

    with col_doc:
        # Native Link Button with Multiline Label
        st.link_button("📚\nDocumentation\nView API docs", "https://platform.openai.com/docs/introduction", use_container_width=True)

    with col_db:
         # Native Button with Multiline Label
        if st.button("🗄️\nDatabase\nCheck DB status", key="btn_check_db", use_container_width=True):
             try:
                # Perform simple connectivity check
                res = run_sql_unified("SELECT 1", db_type=db_type)
                if res and "error" not in str(res).lower():
                     st.toast("✅ Database Connected Successfully!", icon="🚀")
                else:
                     st.toast(f"❌ Connection Issue: {res}", icon="⚠️")
             except Exception as e:
                 st.toast(f"❌ Error Checking DB: {e}", icon="🔥")

    with col_config:
        # Native Button with Multiline Label
        if st.button("⚙️\nConfiguration\nRebuild RAG Index", key="btn_rebuild_rag", use_container_width=True):
            try:
                with st.spinner("Rebuilding Index..."):
                    from rag.rag_retriever import get_rag_retriever
                    rag_agent = get_rag_retriever()
                    result = rag_agent.build_index_from_examples(DEFAULT_EXAMPLES_PATH, force_rebuild=True)
                    if result["success"]:
                        st.toast(f"✅ Rebuilt Index: {result['indexed_count']} examples", icon="🧠")
                    else:
                        st.toast(f"❌ Failed: {result['error']}", icon="⚠️")
            except Exception as e:
                st.toast(f"❌ Error: {str(e)}", icon="🔥") 

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin: 4px 0;'></div>", unsafe_allow_html=True)
    
    # Create container for chat messages
    chat_container = st.container()

def render_chat_bubble(content_html: str, role: str):
    content_html = sanitize_html(content_html)
    if role == "assistant":
        target = st.container()
        with target:
            # Removed extra emojis/icons from HTML structure to use CSS pseudo-elements or cleaner icons
            wrapper_open = "<div class='chat-row assistant'><div class='chat-icon assistant'>🤖</div><div class='chat-bubble assistant'>"
            wrapper_close = "</div></div>"
            st.markdown(f"{wrapper_open}{content_html}{wrapper_close}", unsafe_allow_html=True)
        return target
    else:
        target = st.container()
        with target:
            wrapper_open = "<div class='chat-row user'><div class='chat-bubble user'>"
            wrapper_close = "</div><div class='chat-avatar user'>You</div></div>"
            st.markdown(f"{wrapper_open}{content_html}{wrapper_close}", unsafe_allow_html=True)
        return target

def render_assistant_table(df: pd.DataFrame, title: str = "📊 Query Results"):
    col_left, _ = st.columns([1, 1])
    with col_left:
        st.markdown(
            f"<div class='bubble-box assistant'><div class='bubble-title'>{title}</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(df, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

# Display chat history in the container with custom layout (messenger style)
with chat_container:
        for i, message in enumerate(st.session_state.messages):
            is_user = message.get("role") == "user"
            target_col = render_chat_bubble(message.get("content", ""), "user" if is_user else "assistant")
            
            # Hiển thị SQL đã lưu trong bubble nếu có
            sql_text_hist = get_sql_text(message) if not is_user else None
            if sql_text_hist:
                sql_html = (
                    f"<div class='summary-text'><strong>SQL Query:</strong><br>"
                    f"<pre><code>{escape(sql_text_hist)}</code></pre></div>"
                )
                render_chat_bubble(sql_html, "assistant")
            # Display data table if this message has cached data
            if "data" in message and message["data"] and len(message["data"]) > 0:
                try:
                    df = pd.DataFrame(message["data"])
                    # Ensure columns match original
                    if "data_columns" in message:
                        df = df[message["data_columns"]]
                    st.markdown(f"<div class='chat-results-title {'user' if is_user else 'assistant'}'>📊 Query Results</div>", unsafe_allow_html=True)
                    st.dataframe(df, width="stretch")
                    
                    row_count = message.get("row_count", len(df))
                    if message.get("has_full_data", True):
                        st.caption(f"📈 Total rows: {row_count}")
                    else:
                        st.caption(f"📈 Showing {len(df)} of {row_count} rows (sample)")
                        st.info("💡 Tip: Re-run query to see full results")
                except Exception as e:
                    st.warning(f"Could not display cached data: {e}")
            
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
                                st.plotly_chart(chart_data["chart"], width="stretch")
                            # Display PNG image (for loaded charts)
                            elif "chart_png" in chart_data and chart_data["chart_png"]:
                                # Display with better quality and layout preservation
                                st.image(
                                    chart_data["chart_png"], 
                                    caption=chart_data.get("question", "Chart"), 
                                    width="stretch",
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
    
    # Display user message in chat container (custom bubble)
    with chat_container:
        render_chat_bubble(question, "user")
    
    # Process with agent
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        try:
            # Use Orchestrator Agent
            orchestrator = get_orchestrator()
            start_time = time.perf_counter()
            db_type_to_use = st.session_state.get("db_type", "postgresql")
            result = orchestrator.run_agent(
                user_question=question,
                db_type=db_type_to_use,
                use_retriever=use_semantic_search,
                examples_path=examples_path,
                top_k=top_k
            )
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            # Display assistant response in chat container
            with chat_container:
                if not result["success"]:
                    render_chat_bubble(f"❌ {result['error']}", "assistant")
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
                    # Auto-save conversation (error case)
                    save_conversation()
                else:
                    # Technical details shown between user and assistant reply
                    with st.expander("⚙️ Technical Details", expanded=False):
                        # Intent Classification
                        if "intent" in result:
                            st.markdown(f"**Intent:** {result['intent']}")
                        
                        st.markdown(f"**⏱️ Execution Time:** {duration:.2f}s")
                        
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
                            st.dataframe(result["data"], width="stretch")
                            st.caption(f"Rows: {len(result['data'])}")

                    # Build response content (no SQL inside bubble)
                    response_parts = []
                    
                    # Add natural language summary if available
                    if "response" in result and result["response"]:
                        resp_html = markdown_to_html(str(result["response"]))
                        response_parts.append(f"<div class='summary-text'>{resp_html}</div>")
                    
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
                    
                    # Fallback nếu không có response nào
                    if not response_parts:
                        response_parts.append("See the chart below:")
                    
                    assistant_history_content = "\n\n".join(response_parts)
                    # Bubble 1: summary/analytics
                    render_chat_bubble(assistant_history_content, "assistant")
                    
                    # Bubble 2: SQL (nếu có và không phải visualize)
                    sql_text = get_sql_text(result)
                    if sql_text and result.get("intent") != "visualize":
                        sql_html = (
                            f"<div class='summary-text'><strong>SQL Query:</strong><br>"
                            f"<pre><code>{escape(sql_text)}</code></pre></div>"
                        )
                        render_chat_bubble(sql_html, "assistant")
                    
                    # Bubble 3: main data table (if any)
                    if result["data"] is not None and not result["data"].empty and result.get("intent") != "visualize":
                        render_assistant_table(result["data"])
                        st.caption(f"📈 Total rows: {len(result['data'])}")
                    
                    st.caption(f"⏱️ Processed in {duration:.2f}s")
                    
                    # Prepare message content - include data for persistence
                    message_content = {
                        "role": "assistant", 
                        "content": assistant_history_content
                    }
                    
                    # Save data to message for persistence (limit to 500 rows to avoid memory issues)
                    if result["data"] is not None and not result["data"].empty and result.get("intent") != "visualize":
                        try:
                            row_count = len(result["data"])
                            if row_count <= 500:
                                # Save full data for small results
                                message_content["data"] = result["data"].to_dict('records')
                                message_content["data_columns"] = list(result["data"].columns)
                                message_content["row_count"] = row_count
                                message_content["has_full_data"] = True
                            else:
                                # Save sample for large results
                                sample_df = result["data"].head(500)
                                message_content["data"] = sample_df.to_dict('records')
                                message_content["data_columns"] = list(result["data"].columns)
                                message_content["row_count"] = row_count
                                message_content["has_full_data"] = False
                        except Exception as e:
                            # If serialization fails, at least save metadata
                            message_content["row_count"] = len(result["data"]) if not result["data"].empty else 0
                    
                    # Save SQL query for reference
                    if sql_text:
                        message_content["sql"] = sql_text
                    
                    # Display chart if available
                    if "chart" in result and result["chart"]:
                        st.subheader("📊 Visualization")
                        try:
                            import plotly.graph_objects as go
                            import plotly.io as pio
                            from streamlit import plotly_chart
                            st.plotly_chart(result["chart"], width="stretch")

                            # Save chart as PNG for persistence
                            if "charts" not in st.session_state:
                                st.session_state.charts = []
                            chart_index = len(st.session_state.charts)

                            st.session_state.charts.append({
                                "question": question,
                                "chart": result["chart"],  # Keep original for display
                                "chart_png": None,   # PNG bytes (không lưu)
                                "chart_json": pio.to_json(result["chart"]) if result.get("chart") is not None else None,
                                "timestamp": time.time()
                            })

                            # Add chart index to message
                            message_content["chart_index"] = chart_index

                        except Exception as e:
                            # If it's a Plotly figure, we shouldn't try st.pyplot
                            is_plotly = False
                            try:
                                import plotly.graph_objects as go
                                if isinstance(result["chart"], go.Figure):
                                    is_plotly = True
                            except:
                                pass

                            if is_plotly:
                                st.error(f"Error displaying Plotly chart: {e}")
                            else:
                                try:
                                    st.pyplot(result["chart"])
                                except Exception as e2:
                                    st.error(f"Error displaying chart: {e}. Fallback failed: {e2}")
                    
                    # Add to chat history
                    st.session_state.messages.append(message_content)
                    
                    # Auto-save conversation (success case, after assistant + chart saved)
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
                    
                    st.dataframe(df, width="stretch")
                    st.caption(f"Rows: {len(df)}")
            except Exception as e:
                st.error(str(e))
