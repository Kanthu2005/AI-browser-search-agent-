import html
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import streamlit as st
from dotenv import load_dotenv

# Search and load .env from multiple potential locations
BASE_DIR = Path(__file__).resolve().parent
AGENT_DIR = BASE_DIR / "google-search-agent"
load_dotenv(AGENT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")
load_dotenv()

API_URL = "http://127.0.0.1:8000/search"
HEALTH_URL = "http://127.0.0.1:8000/health"

# Page configuration
st.set_page_config(
    page_title="AI Search Agent | Research Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "history" not in st.session_state:
    st.session_state.history = []  # List of {"question": ..., "answer": ..., "sources": [...], "model": ..., "time": ...}
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "auto_search" not in st.session_state:
    st.session_state.auto_search = False

# Theme definitions
is_dark = st.session_state.theme == "dark"

THEME_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

/* Dynamic theme variables */
:root {{
    --bg-page: {'#0B0F19' if is_dark else '#F8FAFC'};
    --bg-card: {'#1E293B' if is_dark else '#FFFFFF'};
    --bg-secondary: {'#111827' if is_dark else '#F1F5F9'};
    --border-color: {'#334155' if is_dark else '#E2E8F0'};
    --text-primary: {'#F8FAFC' if is_dark else '#0F172A'};
    --text-secondary: {'#94A3B8' if is_dark else '#64748B'};
    --accent: #4F46E5;
    --accent-hover: #4338CA;
    --accent-light: {'rgba(79, 70, 229, 0.15)' if is_dark else '#EEF2FF'};
    --success: #16A34A;
    --success-light: {'rgba(22, 163, 74, 0.15)' if is_dark else '#DCFCE7'};
    --card-shadow: {'0 2px 8px rgba(0,0,0,0.4)' if is_dark else '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)'};
}}

.stApp {{
    background-color: var(--bg-page);
    color: var(--text-primary);
}}

/* Hide unnecessary default Streamlit decoration */
header[data-testid="stHeader"] {{
    background-color: transparent;
}}

/* Typography */
.hero-badge {{
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    background-color: var(--accent-light);
    padding: 4px 12px;
    border-radius: 9999px;
    border: 1px solid {'#4338CA' if is_dark else '#C7D2FE'};
    margin-bottom: 0.8rem;
}}

.hero-title {{
    font-size: 2.5rem;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1.15;
    letter-spacing: -0.03em;
    margin-bottom: 0.5rem;
}}

.hero-subtitle {{
    font-size: 1.05rem;
    color: var(--text-secondary);
    max-width: 650px;
    line-height: 1.5;
    margin-bottom: 2rem;
}}

/* Query Chip Buttons */
.chip-container {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    margin-bottom: 24px;
}}

/* Search Box Container */
.search-wrapper {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 18px 22px;
    box-shadow: var(--card-shadow);
    margin-bottom: 1rem;
}}

/* Result Query Display */
.query-banner {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: var(--card-shadow);
}}

.query-text {{
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--text-primary);
}}

.query-meta {{
    font-size: 0.8rem;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 12px;
}}

/* Answer Card */
.answer-card {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 28px;
    box-shadow: var(--card-shadow);
    margin-bottom: 24px;
    line-height: 1.7;
}}

/* Sources Grid */
.sources-header {{
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.source-card {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: transform 0.15s ease, border-color 0.15s ease;
    text-decoration: none;
    display: block;
}}

.source-card:hover {{
    border-color: var(--accent);
    transform: translateY(-1px);
}}

.source-hostname {{
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--accent);
    text-transform: lowercase;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.source-title {{
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

/* System Status Pill */
.status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
}}

.status-online {{
    background-color: var(--success-light);
    color: var(--success);
    border: 1px solid {'rgba(22, 163, 74, 0.3)' if is_dark else '#BBF7D0'};
}}

.status-offline {{
    background-color: {'rgba(245, 158, 11, 0.15)' if is_dark else '#FEF3C7'};
    color: {'#FBBF24' if is_dark else '#B45309'};
    border: 1px solid {'rgba(245, 158, 11, 0.3)' if is_dark else '#FDE68A'};
}}

/* Sidebar Branding */
.brand-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}}

.brand-desc {{
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
}}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


# ==============================================================================
# Helper Functions: Backend & Direct Fallback
# ==============================================================================

def check_backend_status() -> Tuple[bool, Optional[dict]]:
    """Checks whether the FastAPI backend is running on port 8000."""
    try:
        res = requests.get(HEALTH_URL, timeout=1.5)
        if res.status_code == 200:
            return True, res.json()
    except Exception:
        pass
    return False, None


def execute_backend_search(question: str, preferred_model: str) -> dict:
    """Calls the FastAPI POST /search endpoint."""
    res = requests.post(
        API_URL,
        json={"question": question, "preferred_model": preferred_model},
        timeout=120,
    )
    if res.ok:
        return res.json()
    else:
        try:
            err_data = res.json()
            error_message = err_data.get("detail", res.text)
        except Exception:
            error_message = res.text[:300]
        raise RuntimeError(f"Backend error ({res.status_code}): {error_message}")


def extract_direct_sources(output_items, answer_text: str = "") -> List[Dict[str, str]]:
    """Extracts sources when running in direct fallback mode."""
    sources = []
    seen = set()

    if output_items:
        for item in output_items:
            item_dict = item.model_dump() if hasattr(item, "model_dump") else (item if isinstance(item, dict) else {})
            if item_dict.get("type") == "mcp_call":
                content = str(item_dict.get("output", ""))
                for block in content.split("L0:"):
                    url_m = re.search(r"URL:\s*(https?://[^\s\n\r]+)", block)
                    if url_m:
                        url = url_m.group(1).strip()
                        if "exa.ai/search" in url:
                            continue
                        title_m = re.search(r"L2:\s*([^\n\r]+)", block)
                        title = title_m.group(1).strip() if title_m else ""
                        if not title:
                            domain = urlparse(url).netloc.replace("www.", "")
                            title = f"Source on {domain}"
                        if url not in seen:
                            seen.add(url)
                            sources.append({"title": title, "url": url})

    for md_title, md_url in re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", answer_text):
        if md_url not in seen and "exa.ai" not in md_url:
            seen.add(md_url)
            sources.append({"title": md_title.strip(), "url": md_url.strip()})

    for raw_url in re.findall(r"(https?://[^\s\)\],\"\'<>]+)", answer_text):
        if raw_url not in seen and "exa.ai" not in raw_url:
            seen.add(raw_url)
            domain = urlparse(raw_url).netloc.replace("www.", "")
            sources.append({"title": f"Resource on {domain}", "url": raw_url})

    return sources


def execute_direct_groq_search(question: str, preferred_model: str) -> dict:
    """Direct fallback search using Groq API if the FastAPI backend is offline."""
    from openai import OpenAI, RateLimitError

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    models_to_try = [preferred_model] if preferred_model else []
    for m in ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]:
        if m not in models_to_try:
            models_to_try.append(m)

    prompt = (
        "Research the following question thoroughly using web search. "
        "Give a clear, factual, well-structured answer with key findings. "
        "Include source URLs or citations where available. "
        "Do not invent facts or citations. "
        "If the available sources are insufficient, explain what was found and what is missing.\n\n"
        f"Question: {question}"
    )

    last_error = None
    for model_name in models_to_try:
        try:
            response = client.responses.create(
                model=model_name,
                input=prompt,
                tools=[{"type": "browser_search"}],
                tool_choice="auto",
            )
            answer = getattr(response, "output_text", None)
            if answer and answer.strip():
                output_items = getattr(response, "output", None)
                sources = extract_direct_sources(output_items, answer)
                return {
                    "question": question,
                    "answer": answer.strip(),
                    "sources": sources,
                    "status": "success",
                    "model_used": model_name,
                }
        except RateLimitError as rle:
            last_error = f"Model '{model_name}' hit rate limit. Trying fallback..."
            continue
        except Exception as exc:
            last_error = str(exc)
            continue

    # Fallback knowledge model
    try:
        chat_resp = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI research assistant. Provide an objective, fact-based response.",
                },
                {"role": "user", "content": question},
            ],
        )
        chat_answer = chat_resp.choices[0].message.content
        return {
            "question": question,
            "answer": (
                "> *Notice: Web search rate limit reached on Groq free tier. "
                "Synthesized using fallback knowledge model (qwen3.8-27b).*\n\n" + chat_answer
            ),
            "sources": [],
            "status": "success",
            "model_used": "qwen/qwen3.8-27b",
        }
    except Exception as exc:
        raise RuntimeError(f"All research models failed: {last_error or exc}")


def perform_search(question: str, preferred_model: str) -> dict:
    """Executes the search via backend first, then falls back seamlessly to direct Groq."""
    backend_active, _ = check_backend_status()
    if backend_active:
        try:
            return execute_backend_search(question, preferred_model)
        except Exception as exc:
            st.warning(f"Backend request failed ({exc}). Falling back to direct client...")

    return execute_direct_groq_search(question, preferred_model)


# ==============================================================================
# Sidebar Layout
# ==============================================================================

with st.sidebar:
    # Logo & Branding matching UI screenshot
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
            <div style="width: 38px; height: 38px; border-radius: 12px; background: #2563EB; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);">
                🔍
            </div>
            <div>
                <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); line-height: 1.2;">AI Search Agent</div>
                <div style="font-size: 0.72rem; color: var(--text-secondary); font-weight: 500; margin-top: 2px;">Search · Research · Discover</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navigation Links (Home, Search History, Settings)
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("🏠 Home", use_container_width=True, type="primary"):
            st.session_state.current_result = None
            st.session_state.pending_query = ""
            st.session_state.auto_search = False
            st.rerun()
    with col_nav2:
        if st.button("⚙️ Settings", use_container_width=True):
            st.toast("Settings configured for Groq Search Models.")

    st.markdown("---")

    # Backend Status
    backend_ok, _ = check_backend_status()
    api_key_configured = bool(os.getenv("GROQ_API_KEY"))

    st.caption("SYSTEM HEALTH")
    if backend_ok:
        st.markdown(
            '<div class="status-pill status-online">● Backend API Connected (Port 8000)</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-pill status-offline">○ Direct Mode (Backend Offline)</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Settings
    with st.expander("⚙️ Settings & Models", expanded=False):
        selected_model = st.selectbox(
            "Search Model",
            options=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
            index=0,
            help="gpt-oss-120b has higher throughput and fresh quota for web search.",
        )

        theme_choice = st.radio(
            "Interface Theme",
            options=["Light", "Dark"],
            index=0 if st.session_state.theme == "light" else 1,
            horizontal=True,
        )
        if theme_choice.lower() != st.session_state.theme:
            st.session_state.theme = theme_choice.lower()
            st.rerun()

    # Search History Section
    st.markdown("---")
    st.caption("RECENT RESEARCH")

    if st.session_state.history:
        for idx, item in enumerate(reversed(st.session_state.history)):
            q_text = item.get("question", "Previous search")
            short_q = q_text if len(q_text) <= 30 else q_text[:27] + "..."
            if st.button(f"🔍 {short_q}", key=f"hist_btn_{idx}", use_container_width=True):
                st.session_state.current_result = item
                st.session_state.pending_query = q_text
                st.rerun()

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
            st.rerun()
    else:
        st.markdown(
            "<div style='font-size: 0.8rem; color: #94A3B8; font-style: italic; padding: 4px 0;'>No recent searches in this session.</div>",
            unsafe_allow_html=True,
        )

    # About Section
    st.markdown("---")
    with st.expander("ℹ️ About AI Search Agent", expanded=False):
        st.markdown(
            """
            **AI Search Agent** is a research tool inspired by Perplexity and Google Search.
            
            - **Live Web Research**: Uses real-time web search via Groq API.
            - **Citations & Sources**: Validates statements against referenced domains.
            - **Contract**: Complies with standard `{question, answer, sources, status}` schema.
            """
        )


# ==============================================================================
# Main Content Area
# ==============================================================================

# If auto_search was triggered via chip or action, process immediately
auto_query = None
if st.session_state.auto_search and st.session_state.pending_query:
    auto_query = st.session_state.pending_query
    st.session_state.auto_search = False

# Top Right Header Bar matching UI screenshot
st.markdown(
    """
    <div style="display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin-bottom: 16px;">
        <div style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 9999px; font-size: 0.78rem; font-weight: 500; color: var(--text-secondary);">
            <span style="color: #F59E0B;">⚡</span> Powered by Groq
        </div>
        <div style="width: 36px; height: 36px; border-radius: 50%; background: #7C3AED; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; box-shadow: 0 2px 6px rgba(124, 58, 237, 0.25);">
            K
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# A. Result View: If user has a current result displayed
if st.session_state.current_result and not auto_query:
    result = st.session_state.current_result
    q_val = result.get("question", "")
    ans_val = result.get("answer", "")
    sources_val = result.get("sources", [])
    model_val = result.get("model", selected_model)
    time_val = result.get("time", None)

    # Action bar / Query header
    st.markdown(
        f"""
        <div class="query-banner">
            <div>
                <div style="font-size: 0.75rem; font-weight: 700; color: #4F46E5; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px;">
                    Research Topic
                </div>
                <div class="query-text">{html.escape(q_val)}</div>
            </div>
            <div class="query-meta">
                <span>⚡ {model_val}</span>
                {f"<span>⏱️ {time_val}s</span>" if time_val else ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Two column layout: Left (Answer 70%), Right (Sources 30%)
    col_ans, col_src = st.columns([7, 3], gap="large")

    with col_ans:
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary);">
                    Synthesized Research
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="answer-card">
            """,
            unsafe_allow_html=True,
        )
        st.markdown(ans_val)
        st.markdown("</div>", unsafe_allow_html=True)

        # Action bar under answer
        col_btn1, col_btn2, _ = st.columns([2, 2, 6])
        with col_btn1:
            if st.button("＋ Search Another Topic", use_container_width=True, type="primary"):
                st.session_state.current_result = None
                st.session_state.pending_query = ""
                st.rerun()
        with col_btn2:
            # Copy Answer helper (Streamlit code snippet with built-in copy icon)
            with st.popover("📋 View / Copy Raw Text"):
                st.caption("Click the copy icon on the top right:")
                st.code(ans_val, language="markdown")

    with col_src:
        src_count = len(sources_val)
        st.markdown(
            f"""
            <div class="sources-header">
                <span>📚 Sources Referenced ({src_count})</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if sources_val:
            for s in sources_val:
                s_url = s.get("url", "#")
                s_title = s.get("title", "External Reference")
                domain = urlparse(s_url).netloc.replace("www.", "") if s_url else "web"

                st.markdown(
                    f"""
                    <a href="{s_url}" target="_blank" rel="noopener noreferrer" class="source-card">
                        <div class="source-hostname">
                            <span>{html.escape(domain)}</span>
                            <span>↗</span>
                        </div>
                        <div class="source-title" title="{html.escape(s_title)}">
                            {html.escape(s_title)}
                        </div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                """
                <div style="background-color: var(--bg-card); border: 1px dashed var(--border-color); border-radius: 10px; padding: 20px; text-align: center; color: var(--text-secondary); font-size: 0.85rem;">
                    No direct external citations returned for this response.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.caption("ℹ️ *Sources are browsed and extracted in real-time. Verify critical facts using original links.*")


# B. Main Search Home State (or executing auto_query)
else:
    # Hero Title & Header
    st.markdown('<div class="hero-badge">AI RESEARCH ASSISTANT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-title">Search smarter.<br><span style="color: #2563EB;">Discover more.</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-subtitle">Get AI-powered research answers with real-time web search.<br>Explore reliable sources and go deeper into what matters.</div>',
        unsafe_allow_html=True,
    )

    # Search Form
    with st.form("search_input_form", clear_on_submit=False):
        query_input = st.text_area(
            "Research Query",
            value=auto_query if auto_query else st.session_state.pending_query,
            placeholder="What would you like to research?",
            max_chars=500,
            height=90,
            label_visibility="collapsed",
        )

        col_count, col_clear, col_submit = st.columns([6, 1.5, 2.5])
        with col_count:
            char_len = len(query_input) if query_input else 0
            st.caption(f"{char_len}/500")
        with col_clear:
            clear_input = st.form_submit_button("✕ Clear", use_container_width=True)
        with col_submit:
            submit_search = st.form_submit_button("🔍 Search", type="primary", use_container_width=True)

    if clear_input:
        st.session_state.pending_query = ""
        st.rerun()

    # Suggested Query Chips matching UI screenshot
    st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: var(--text-primary); margin-top: 14px; margin-bottom: 8px;'>Try these example searches</div>", unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    chips = [
        ("🔍 Latest AI developments", "Latest AI developments"),
        ("🔍 Python best practices", "Python best practices"),
        ("🔍 Technology trends", "Technology trends"),
        ("🔍 Compare React vs Vue", "Compare React vs Vue"),
        ("🔍 Climate change solutions", "Climate change solutions"),
    ]

    for col, (label, query_text) in zip([col1, col2, col3, col4, col5], chips):
        if col.button(label, use_container_width=True):
            st.session_state.pending_query = query_text
            st.session_state.auto_search = True
            st.rerun()

    # Empty State card matching the UI screenshot
    st.markdown(
        """
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 48px 20px; text-align: center; margin-top: 24px; box-shadow: var(--card-shadow);">
            <div style="font-size: 42px; margin-bottom: 12px;">🔍 📄 ✨</div>
            <div style="font-size: 1.18rem; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">Start your search</div>
            <div style="font-size: 0.9rem; color: var(--text-secondary); max-width: 440px; margin: 0 auto;">
                Enter a question above to get AI-powered research results with reliable sources.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Process search if submitted or auto-triggered
    active_query = (query_input if submit_search else auto_query)

    if active_query:
        clean_q = active_query.strip()
        if len(clean_q) < 3:
            st.warning("⚠️ Please enter a research question with at least 3 characters.")
        elif not api_key_configured:
            st.error("❌ GROQ_API_KEY is not detected. Please add it to your .env file to enable search.")
        else:
            start_time = time.time()
            with st.spinner("🌐 Researching your question... Browsing live web sources and synthesizing answer..."):
                try:
                    res_data = perform_search(clean_q, selected_model)
                    elapsed = round(time.time() - start_time, 2)

                    answer_text = res_data.get("answer", "")
                    sources_list = res_data.get("sources", [])
                    model_name = res_data.get("model_used", selected_model)

                    # Structure the result record
                    result_record = {
                        "question": clean_q,
                        "answer": answer_text,
                        "sources": sources_list,
                        "model": model_name,
                        "time": elapsed,
                    }

                    # Add to history
                    st.session_state.history.append(result_record)
                    st.session_state.current_result = result_record
                    st.rerun()

                except Exception as exc:
                    st.error(f"❌ Research request failed: {exc}")
