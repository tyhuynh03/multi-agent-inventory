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
        
        # Display segments as dropdown/expander; controls only when expanded
        for i, filename in enumerate(segment_files):
            try:
                with open(f"data/chat_segments/{filename}", "r", encoding="utf-8") as f:
                    segment_data = json.load(f)
                
                segment_name = segment_data.get('name', filename.replace('.json', ''))
                with st.expander(segment_name, expanded=False):
                    col_load, col_delete = st.columns([1, 1])
                    with col_load:
                        if st.button("📂 Load", key=f"load_segment_{i}", width="stretch"):
                            load_chat_segment(filename)
                    with col_delete:
                        if st.button("🗑️ Delete", key=f"delete_segment_{i}", width="stretch"):
                            delete_chat_segment(filename)
                    
                    # Inline rename input (full width, centered text)
                    new_name = st.text_input(
                        "Rename:",
                        value=segment_name,
                        key=f"rename_input_{i}",
                        label_visibility="visible",
                    )
                    if st.button("✓ Rename", key=f"rename_confirm_{i}", width="stretch"):
                        if new_name.strip() and new_name.strip() != segment_name:
                            rename_chat_segment(filename, new_name.strip())
                
            except Exception as e:
                st.error(f"Error loading segment {filename}: {e}")
                
    except Exception as e:
        st.error(f"Error loading chat segments: {e}")

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

def rename_chat_segment(filename, new_name):
    """Rename a chat segment"""
    try:
        # Read current segment data
        with open(f"data/chat_segments/{filename}", "r", encoding="utf-8") as f:
            segment_data = json.load(f)
        
        # Update name
        segment_data["name"] = new_name.strip()
        
        # Create new filename
        new_filename = f"{new_name.strip().replace(' ', '_')}.json"
        new_filepath = f"data/chat_segments/{new_filename}"
        
        # Save with new name
        with open(new_filepath, "w", encoding="utf-8") as f:
            json.dump(segment_data, f, ensure_ascii=False, indent=2)
        
        # Delete old file if filename changed
        if filename != new_filename:
            os.remove(f"data/chat_segments/{filename}")
        
        st.success(f"✅ Renamed to '{new_name.strip()}'")
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

    /* Tăng cỡ chữ tổng thể */
    :root { font-size: 17px; }
    body, [data-testid="stAppViewContainer"] .main {
        font-size: 17px;
        line-height: 1.6;
    }
    /* Form controls to 16px cho gọn */
    input, textarea, button, select, label, .stMarkdown, .stTextInput, .stTextArea {
        font-size: 16px !important;
    }
    
/* ---------------------------------------------------
   FIX INPUT BAR — ALWAYS ON TOP, RESPONSIVE
--------------------------------------------------- */
div[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 24px !important;  /* cách đáy một khoảng hợp lý */
    z-index: 999 !important;
    display: flex !important;
    justify-content: center;
    background: transparent !important;
    padding: 0 1.5cm !important;  /* chừa lề hai bên ~1.5cm */
    width: clamp(1300px, 95vw, 1900px) !important;  /* mặc định khi sidebar mở */
    box-sizing: border-box !important;
}

div[data-testid="stChatInput"] > div {
    margin: 0 auto !important;  /* luôn căn giữa thanh input */
}



/* Giữ nội dung không bị che */
[data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 8px !important;   /* giảm khoảng trống đầu trang */
    padding-bottom: 150px !important;
}

/* ---------------------------------------------------
   CHAT BUBBLES 
--------------------------------------------------- */
    /* Preserve bubble-specific colors */
    .chat-bubble.user { color: var(--chat-user-text) !important; }
    .chat-bubble.assistant { color: var(--chat-assistant-text) !important; }
    .chat-bubble code, .chat-bubble pre { color: inherit !important; }
    .summary-text { 
        font-size: 15px; 
        line-height: 1.6; 
    font-family: 'Inter', 
    sans-serif; 
        white-space: pre-wrap;
    }
    
/* COMMON BUBBLE SETTINGS */
[data-testid="stChatMessage"] {
    margin: 8px 0 !important;
        display: flex !important;
        width: 100% !important;
    }
    
/* USER (BÊN PHẢI) */
[data-testid="stChatMessage"][data-message-author="user"] {
    justify-content: flex-end !important;
    flex-direction: row !important; /* bubble trước, avatar bên phải */
}

[data-testid="stChatMessage"][data-message-author="user"] [data-testid="stChatAvatar"] {
    background: #1d4ed8 !important;
    color: white !important;
    width: 36px !important;
    height: 36px !important;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
}

[data-testid="stChatMessage"][data-message-author="user"] [data-testid="stChatMessageContent"] {
    background: #2b7bff !important;
    color: white !important;
    padding: 12px 14px !important;
    border-radius: 16px 16px 4px 16px !important;
    max-width: 45% !important; /* hẹp lại giống ảnh */
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    line-height: 1.5;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    word-break: break-word;
    margin-left: auto !important; /* dồn sát phải */
}

/* DARK MODE USER */
@media (prefers-color-scheme: dark) {
    [data-testid="stChatMessage"][data-message-author="user"] [data-testid="stChatMessageContent"] {
        background: #1f4e8c !important;
        color: #e8f0ff !important;
    }
}

/* ASSISTANT (BÊN TRÁI) */
[data-testid="stChatMessage"][data-message-author="assistant"] {
    justify-content: flex-start !important;
    flex-direction: row !important;
}

[data-testid="stChatMessage"][data-message-author="assistant"] [data-testid="stChatAvatar"] {
    background: #d1d5db !important; 
    color: #111 !important;
    width: 36px !important;
    height: 36px !important;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    font-weight: 600;
}

[data-testid="stChatMessage"][data-message-author="assistant"] [data-testid="stChatMessageContent"] {
    background: #f0f0f0 !important;
    color: #000 !important;
    padding: 12px 16px !important;
    border-radius: 16px 16px 16px 4px !important;
    max-width: 60% !important;
    font-family: 'Inter', sans-serif;
    font-size: 15px;
        line-height: 1.5;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    word-break: break-word;
}

/* ASSISTANT DARK MODE */
@media (prefers-color-scheme: dark) {
    [data-testid="stChatMessage"][data-message-author="assistant"] [data-testid="stChatMessageContent"] {
        background: #303030 !important;
        color: white !important;
    }
    [data-testid="stChatMessage"][data-message-author="assistant"] [data-testid="stChatAvatar"] {
        background: #4b5563 !important;
        color: white !important;
    }
}

/* ---------------------------------------------------
   OVERRIDE USING CHAT-ROW / CHAT-BUBBLE CLASSES
   (đảm bảo so le: user bên phải, assistant bên trái)
--------------------------------------------------- */
.chat-row {
    display: flex !important;
    width: 100% !important;
    align-items: flex-end !important;
    gap: 10px !important;
    margin: 10px 0 !important;
}
.chat-row.user {
    justify-content: flex-end !important;
    flex-direction: row !important;  /* bubble trước, avatar sau */
}
.chat-row.assistant {
    justify-content: flex-start !important;
    flex-direction: row !important;
    align-items: center !important;
}

.chat-row.user .chat-bubble.user {
    background: #2b7bff !important;
    color: #fff !important;
    padding: 12px 14px !important;
    border-radius: 16px 16px 4px 16px !important;
    max-width: 48% !important;
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    line-height: 1.5;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    word-break: break-word;
}
.chat-row.user .chat-avatar {
    margin-left: 8px !important;
    width: 36px !important;
    height: 36px !important;
    border-radius: 50% !important;
    background: #303030 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 18px !important;
    color: #fff !important;
    font-weight: 700 !important;
    flex-shrink: 0 !important;
}

.chat-row.assistant .chat-bubble.assistant {
    background: #f0f0f0 !important;
    color: #000 !important;
    padding: 12px 16px !important;
    border-radius: 16px 16px 16px 4px !important;
    max-width: 60% !important;
    font-family: 'Inter', sans-serif;
        font-size: 15px;
    line-height: 1.5;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    word-break: break-word;
}
.chat-row.assistant .chat-icon {
    margin-right: 10px !important;
    width: 42px !important;
    height: 42px !important;
    border-radius: 50% !important;
    background: #d1d5db !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 20px !important;
    color: #111 !important;
    flex-shrink: 0 !important;
}

@media (prefers-color-scheme: dark) {
    .chat-row.user .chat-bubble.user { background: #0ea5e9 !important; }
    .chat-row.user .chat-avatar { background: #0284c7 !important; }
    .chat-row.assistant .chat-bubble.assistant { background: #DDDDDD !important; color: #000 !important; }
    .chat-row.assistant .chat-icon { background: #DDDDDD !important; color: #000 !important; }
}

</style>

"""), unsafe_allow_html=True)

# JS chỉnh width input theo trạng thái sidebar
st.markdown(textwrap.dedent("""
<script>
function adjustChatInputWidth() {
    const container = document.querySelector('div[data-testid="stChatInput"]');
    const bar = container ? container.querySelector(':scope > div') : null;
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    if (!container || !bar) return;
    const sidebarHidden = sidebar && getComputedStyle(sidebar).display === "none";
    if (sidebarHidden) {
        bar.style.width = "clamp(1400px, 97vw, 2200px)";
    } else {
        bar.style.width = "clamp(1300px, 95vw, 1900px)";
    }

    // Toggle RG logo overlay when sidebar is hidden
    const rg = document.getElementById('logo-rg-container');
    if (rg) {
        rg.style.display = sidebarHidden ? 'block' : 'none';
    }
}

adjustChatInputWidth();
window.addEventListener('resize', adjustChatInputWidth);
new MutationObserver(adjustChatInputWidth).observe(document.body, { childList: true, subtree: true });
</script>
"""), unsafe_allow_html=True)



# Main logo centered in main content
logo_path = os.path.abspath("assets/logo.png")
logo_cntt_path = os.path.abspath("assets/logo_cntt.png")

# Centered header (logo + title) gọn, sát top
header_html_parts = []
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode("utf-8")
    header_html_parts.append(
        f"<img src='data:image/png;base64,{logo_b64}' width='320' style='display:block; margin:0 auto 6px auto;' />"
    )
header_html_parts.append(
    "<h1 style='text-align:center; margin:0; padding:0; font-size:30px;'>🤖 Multi-Agent for Inventory</h1>"
)
st.markdown(
    "<div style='text-align:center; margin-top:0; margin-bottom:8px;'>"
    + "".join(header_html_parts) +
    "</div>",
    unsafe_allow_html=True,
)

# Sidebar logo CNTT
with st.sidebar:
    if os.path.exists(logo_cntt_path):
        st.image(logo_cntt_path, width=220)

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

with st.sidebar:
    # Save as chat segment
    st.header("💾 Save Segment")
    segment_name = st.text_input("Segment name:", value="", placeholder="Enter segment name...", key="save_segment_input")
    if st.button("💾 Save as Chat Segment", width="stretch", key="save_segment_btn"):
        if segment_name.strip():
            # Save with custom name
            try:
                if not st.session_state.messages:
                    st.warning("No conversation to save")
                else:
                    # Serialize charts (only JSON) to avoid non-serializable Plotly objects
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
                            st.warning(f"Could not serialize chart for segment: {e}")
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
                    
                    st.success(f"✅ Chat segment '{segment_name.strip()}' saved!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error saving chat segment: {e}")
        else:
            save_chat_segment()
    
    st.divider()
    
    # Chat Segments header with Clear button on the same row
    col_segments, col_clear = st.columns([3, 1])
    with col_segments:
        st.header("📚 Chat Segments")
    with col_clear:
        if st.button("🗑️", width="stretch", help="Clear chat history", key="clear_chat_btn"):
            st.session_state.messages = []
            st.session_state.charts = []
            # Clear conversation file
            if os.path.exists("data/conversation.json"):
                try:
                    os.remove("data/conversation.json")
                except:
                    pass
            st.rerun()
    
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
    
    # Button Check DB
    if st.button("Check DB", width="stretch", key="check_db_btn"):
        try:
            if db_type == "postgresql":
                # Test PostgreSQL connection
                df, error = run_sql_unified("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'", "postgresql")
                if error:
                    st.error(f"PostgreSQL error: {error}")
                else:
                    st.success("✅ Connected!")
                    # Get table names
                    df_tables, _ = run_sql_unified("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name", "postgresql")
                    st.write("Tables:")
                    # Display table names with proper formatting for sidebar
                    table_list = df_tables['table_name'].tolist()
                    st.code(str(table_list), language="bash")
            else:
                db = get_db(db_path, "sqlite")
                st.success("✅ Connected. Tables:")
                st.code(db.get_usable_table_names(), language="bash")
        except Exception as e:
            st.error(f"DB error: {e}")
    
    # Button dưới
    if st.button("🔄 Rebuild RAG Index", width="stretch"):
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
tab_text2sql, tab_sql_console = st.tabs(["AI Assistant", "SQL Console"]) 

with tab_text2sql:
    st.write("Enter your question in English. The app will generate a `SELECT` query and run it on PostgreSQL.")
    
    
    
    # Create container for chat messages
    chat_container = st.container()
    
    def render_chat_bubble(content_html: str, role: str):
        content_html = sanitize_html(content_html)
        if role == "assistant":
            target = st.container()
            with target:
                wrapper_open = "<div class='chat-row assistant'><div class='chat-icon'>🤖</div><div class='chat-bubble assistant'>"
                wrapper_close = "</div></div>"
                st.markdown(f"{wrapper_open}{content_html}{wrapper_close}", unsafe_allow_html=True)
            return target
        else:
            target = st.container()
            with target:
                wrapper_open = "<div class='chat-row user'><div class='chat-bubble user'>"
                wrapper_close = "</div><div class='chat-avatar'>🙂</div></div>"
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
                result = orchestrator.run_agent(
                    user_question=question,
                    db_type="postgresql",
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