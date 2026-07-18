"""
Multimodal Chatbot — Streamlit web app, "Claude-style layout, teal theme".

Layout mirrors the clean, minimal chat-interface pattern popularized by
Claude.ai: a narrow centered column, plain-text assistant replies with no
bubble/border, a subtle rounded box only around the user's own messages,
a pill-shaped input bar, a sidebar with a "New chat" button and a running
list of past conversations, and file/image upload support. The color
palette and icon are original — deep navy with a teal/cyan accent — not
Claude's actual branding or logo.

Run locally with:  streamlit run app.py
Deploy for free on: https://share.streamlit.io (Streamlit Community Cloud)
"""

import base64
import streamlit as st
from config import validate_config
from memory import LongTermMemory
from text_gen import create_chat, get_response
from file_handler import build_message_content
import rag


def _load_background_base64(path: str) -> str:
    """Reads a local image and returns it as a base64 string for use in CSS."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


_BG_IMAGE_B64 = _load_background_base64("assets/chat_bot_image.jpg")

st.set_page_config(page_title="Multimodal Chatbot", page_icon="◆", layout="centered")

SUGGESTIONS = [
    "Explain quantum computing simply",
    "Draw a cat astronaut in space",
    "Write a short poem about rain",
    "Animate a sunset over mountains",
]


# =========================================================================
# THEME
# =========================================================================
_APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #0B0F17;
    --bg-glow: #101826;
    --surface: #141B26;
    --surface-2: #1C2531;
    --text: #E8EDF2;
    --text-dim: #8A97A8;
    --accent: #2DD4BF;
    --accent-2: #38BDF8;
    --accent-dim: #1B8F82;
    --border: #253141;
}

* { font-family: 'Inter', sans-serif; }

/* Catch-all: every button gets a matched background+text pair here FIRST,
   so nothing can end up with mismatched colors from Streamlit's own
   defaults. More specific rules further down (sidebar, chips, etc.)
   override this safely since they come later in the file. */
.stButton button, [data-testid="stButton"] button, button[kind] {
    background: var(--surface-2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
}


/* Custom background image, dimmed with a dark overlay so chat text/bubbles stay readable */
.stApp {
    background-image:
        linear-gradient(rgba(11, 15, 23, 0.82), rgba(11, 15, 23, 0.88)),
        url("data:image/jpeg;base64,__BG_IMAGE_B64__");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    background-repeat: no-repeat;
    color: var(--text);
}
#MainMenu, footer, header {visibility: hidden;}

.block-container {
    max-width: 720px;
    padding-top: 2rem;
    padding-bottom: 8rem;
}

/* Custom scrollbar — thin, unobtrusive, matches theme */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surface-2); border-radius: 8px; border: 2px solid var(--bg); }
::-webkit-scrollbar-thumb:hover { background: var(--accent-dim); }

/* ---- Brand mark: gradient square instead of flat color ---- */
.mmc-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 2.5rem; }
.mmc-brand-mark {
    width: 30px; height: 30px; border-radius: 9px;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; color: #04211D; font-size: 1rem;
    box-shadow: 0 2px 10px rgba(45, 212, 191, 0.25);
}
.mmc-brand-name { font-weight: 600; font-size: 1rem; color: var(--text); letter-spacing: -0.01em; }

.mmc-greeting {
    font-size: 1.65rem; font-weight: 600; color: var(--text); margin: 3rem 0 1.5rem 0;
    letter-spacing: -0.01em;
    animation: mmcFadeUp 0.5s ease both;
}
.mmc-greeting span {
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent-2) 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}

/* ---- Suggestion chips (empty-state starter prompts) ----
   Note: these buttons are NOT actually nested inside .mmc-chip-row in the
   real DOM (Streamlit renders that div as a sibling, not a parent), so we
   target them via the main content region + their key-based wrapper class
   instead, which Streamlit does reliably attach. */
[data-testid="stMain"] div[class*="st-key-chip_"] button,
[data-testid="stMain"] .mmc-chip-row + div .stButton button {
    background: var(--surface) !important;
    color: var(--text-dim) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    font-weight: 400 !important;
    font-size: 0.88rem !important;
    text-align: left !important;
    padding: 12px 14px !important;
    transition: all 0.15s ease !important;
    white-space: normal !important;
    height: auto !important;
}
[data-testid="stMain"] div[class*="st-key-chip_"] button:hover,
[data-testid="stMain"] .mmc-chip-row + div .stButton button:hover {
    border-color: var(--accent) !important;
    color: var(--text) !important;
    background: var(--surface-2) !important;
    transform: translateY(-1px);
}

/* ---- Messages ---- */
.mmc-row { display: flex; margin-bottom: 22px; width: 100%; animation: mmcFadeUp 0.35s ease both; }
.mmc-row.user { justify-content: flex-end; }

.mmc-bubble { font-size: 0.98rem; line-height: 1.65; white-space: pre-wrap; }
.mmc-bubble.user {
    background: var(--surface-2); color: var(--text);
    padding: 10px 16px; border-radius: 18px; max-width: 80%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.mmc-bubble.assistant { background: transparent; color: var(--text); padding: 0; max-width: 100%; }

.mmc-assistant-row {
    display: flex; gap: 12px; margin-bottom: 22px; align-items: flex-start;
    animation: mmcFadeUp 0.35s ease both;
}
.mmc-avatar {
    flex-shrink: 0; width: 26px; height: 26px; border-radius: 8px;
    background: linear-gradient(135deg, var(--accent-dim) 0%, #0F5850 100%);
    display: flex; align-items: center; justify-content: center;
    color: var(--accent); font-size: 0.85rem; font-weight: 700; margin-top: 2px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

/* ---- Typing indicator (animated dots, shown while waiting on a reply) ---- */
.mmc-typing { display: flex; gap: 12px; align-items: center; margin-bottom: 22px; }
.mmc-typing-dots { display: flex; gap: 4px; padding: 6px 0; }
.mmc-typing-dots span {
    width: 6px; height: 6px; border-radius: 50%; background: var(--text-dim);
    animation: mmcBounce 1.2s infinite ease-in-out both;
}
.mmc-typing-dots span:nth-child(1) { animation-delay: -0.28s; }
.mmc-typing-dots span:nth-child(2) { animation-delay: -0.14s; }

@keyframes mmcBounce {
    0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}
@keyframes mmcFadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

.mmc-media-wrap { margin: 10px 0 6px 0; max-width: 340px; }
.mmc-media-wrap img, .mmc-media-wrap video {
    width: 100%; border-radius: 12px; border: 1px solid var(--border); display: block;
    box-shadow: 0 4px 16px rgba(0,0,0,0.35);
    transition: transform 0.2s ease;
}
.mmc-media-wrap img:hover { transform: scale(1.01); }

.mmc-attachment-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--surface-2); border: 1px solid var(--border);
    color: var(--text-dim); font-size: 0.78rem;
    padding: 4px 10px; border-radius: 20px; margin-bottom: 8px;
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
.mmc-sidebar-label {
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-dim); margin: 1.2rem 0 0.5rem 0;
}
.mmc-greeting {
    font-size: 1.05rem; font-weight: 600; color: var(--text);
    margin-bottom: 0.8rem;
}
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] p { color: var(--text-dim); }
[data-testid="stSidebar"] .stTextInput input, [data-testid="stSidebar"] .stSelectbox div {
    background: var(--surface-2); color: var(--text);
    border: 1px solid var(--border); border-radius: 8px;
}
[data-testid="stSidebar"] .stButton button {
    background: transparent; color: var(--text);
    border: 1px solid transparent; font-weight: 500; border-radius: 8px;
    text-align: left; transition: all 0.15s ease;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: var(--surface-2); border-color: var(--border);
}
.mmc-newchat button {
    background: var(--accent) !important; color: #04211D !important;
    font-weight: 600 !important; border: none !important;
    box-shadow: 0 2px 8px rgba(45, 212, 191, 0.2) !important;
}
.mmc-newchat button:hover {
    background: #4FE3D1 !important;
    box-shadow: 0 2px 12px rgba(45, 212, 191, 0.35) !important;
    transform: translateY(-1px);
}
.mmc-convo-active button {
    border-color: var(--accent) !important;
    background: var(--accent-dim) !important;
    color: var(--text) !important;
}

/* ---- Chat input, with built-in paperclip attach icon ---- */
/* Streamlit wraps the input in its own solid-background bottom bar by
   default — make that transparent so the page background shows through. */
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"],
[data-testid="stBottom"] > div, .stChatFloatingInputContainer {
    background: transparent !important;
}
[data-testid="stChatInput"] {
    background: rgba(28, 37, 49, 0.75);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid var(--border); border-radius: 28px; padding: 4px 8px;
    outline: none !important; box-shadow: 0 4px 20px rgba(0,0,0,0.25) !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent); outline: none !important;
    box-shadow: 0 4px 20px rgba(45, 212, 191, 0.15) !important;
}
[data-testid="stChatInput"] *:focus, [data-testid="stChatInput"] *:focus-visible {
    outline: none !important; box-shadow: none !important;
}
[data-testid="stChatInput"] textarea { color: var(--text) !important; }

[data-testid="stChatInputSubmitButton"], [data-testid="stChatInput"] button {
    color: var(--text-dim) !important; transition: color 0.15s ease;
}
[data-testid="stChatInput"] button:hover { color: var(--accent) !important; }

[data-testid="stChatInputFilePreview"] {
    background: var(--surface-2); border: 1px solid var(--border);
    border-radius: 10px; color: var(--text-dim);
}

hr { border-color: var(--border); }
</style>
"""
st.markdown(_APP_CSS.replace("__BG_IMAGE_B64__", _BG_IMAGE_B64), unsafe_allow_html=True)


def build_system_prompt(long_term_memory: LongTermMemory) -> str:
    base = (
        "You are a helpful multimodal assistant. You can chat normally, and "
        "you can also generate images and videos when the user asks for them "
        "using the tools available to you. If the user attaches an image, "
        "PDF, or document, read/look at it and respond to what it contains."
    )
    memory_snippet = long_term_memory.as_system_prompt_snippet()
    if memory_snippet:
        return f"{base}\n\n{memory_snippet}"
    return base


def render_message(role: str, content: str, images=None, videos=None, attachment_name=None):
    if attachment_name:
        st.markdown(
            f'<div class="mmc-row user"><div class="mmc-attachment-chip">📎 {attachment_name}</div></div>',
            unsafe_allow_html=True,
        )
    if role == "user":
        st.markdown(
            f'<div class="mmc-row user"><div class="mmc-bubble user">{content}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="mmc-assistant-row">'
            f'<div class="mmc-avatar">✦</div>'
            f'<div class="mmc-bubble assistant">{content}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    for img_path in (images or []):
        st.markdown('<div class="mmc-media-wrap">', unsafe_allow_html=True)
        st.image(img_path, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    for vid_path in (videos or []):
        st.markdown('<div class="mmc-media-wrap">', unsafe_allow_html=True)
        st.video(vid_path)
        st.markdown('</div>', unsafe_allow_html=True)


def new_conversation():
    """Creates a fresh chat session + display history and makes it active."""
    conv_id = f"conv_{len(st.session_state.conversations)}_{st.session_state.next_conv_num}"
    st.session_state.next_conv_num += 1
    st.session_state.conversations[conv_id] = {
        "title": "New chat",
        "chat": create_chat(build_system_prompt(st.session_state.long_term_memory)),
        "display_history": [],
    }
    st.session_state.active_conv_id = conv_id


def process_turn(active_conv, user_input: str, uploaded_file=None):
    """Handles one full exchange: retrieve relevant knowledge-base context
    (if any exists), render the user's message, show a live typing
    indicator while Gemini responds, then render the reply. Shared by both
    the chat input and the suggestion chips so behavior stays identical no
    matter how a message was sent."""
    attachment_name = uploaded_file.name if uploaded_file else None

    active_conv["display_history"].append({
        "role": "user", "content": user_input, "attachment_name": attachment_name,
    })
    render_message("user", user_input, attachment_name=attachment_name)

    if active_conv["title"] == "New chat":
        title_source = user_input or (attachment_name or "New chat")
        active_conv["title"] = title_source[:40] + ("..." if len(title_source) > 40 else "")

    typing_placeholder = st.empty()
    typing_placeholder.markdown(
        '<div class="mmc-typing"><div class="mmc-avatar">✦</div>'
        '<div class="mmc-typing-dots"><span></span><span></span><span></span></div></div>',
        unsafe_allow_html=True,
    )

    # Retrieve relevant knowledge-base context, if any documents were added
    augmented_text = user_input
    if user_input and rag.has_documents():
        retrieved_chunks = rag.query(user_input)
        augmented_text = rag.build_augmented_content(user_input, retrieved_chunks)

    content = build_message_content(augmented_text, uploaded_file)

    reply, images, videos = get_response(active_conv["chat"], content)
    typing_placeholder.empty()

    render_message("assistant", reply, images, videos)
    active_conv["display_history"].append(
        {"role": "assistant", "content": reply, "images": images, "videos": videos}
    )


# --- One-time setup ---
try:
    validate_config()
except EnvironmentError as e:
    st.error(str(e))
    st.stop()

if "long_term_memory" not in st.session_state:
    st.session_state.long_term_memory = LongTermMemory()

if "conversations" not in st.session_state:
    st.session_state.conversations = {}
    st.session_state.next_conv_num = 1
    new_conversation()

active = st.session_state.conversations[st.session_state.active_conv_id]


# --- Sidebar: New chat, conversation list, memory drawer ---
with st.sidebar:
    st.markdown('<div class="mmc-newchat">', unsafe_allow_html=True)
    if st.button("+ New chat", use_container_width=True):
        new_conversation()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="mmc-sidebar-label">Conversations</div>', unsafe_allow_html=True)
    for conv_id in reversed(list(st.session_state.conversations.keys())):
        conv = st.session_state.conversations[conv_id]
        is_active = conv_id == st.session_state.active_conv_id
        css_class = "mmc-convo-active" if is_active else ""
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(conv["title"], key=f"select_{conv_id}", use_container_width=True):
            st.session_state.active_conv_id = conv_id
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="mmc-sidebar-label">Memory</div>', unsafe_allow_html=True)
    facts = st.session_state.long_term_memory.facts

    # Pull a name out of stored facts (case-insensitive key match) for a
    # friendly greeting at the top of the memory panel.
    stored_name = None
    for k, v in facts.items():
        if k.strip().lower() == "name":
            stored_name = v
            break

    if stored_name:
        st.markdown(f'<div class="mmc-greeting">👋 Hi, {stored_name}</div>', unsafe_allow_html=True)

    if facts:
        for k, v in facts.items():
            st.markdown(f"**{k}**  \n{v}")
    else:
        st.caption("Nothing remembered yet.")

    st.markdown("**Add a fact**")
    new_key = st.text_input("Key", key="new_key", placeholder="e.g. name", label_visibility="collapsed")
    new_value = st.text_input("Value", key="new_value", placeholder="e.g. Harika", label_visibility="collapsed")
    if st.button("Remember", use_container_width=True):
        if new_key and new_value:
            st.session_state.long_term_memory.remember(new_key.strip(), new_value.strip())
            st.rerun()

    if facts:
        forget_key = st.selectbox("Choose a key", options=list(facts.keys()), label_visibility="collapsed")
        if st.button("Forget", use_container_width=True):
            st.session_state.long_term_memory.forget(forget_key)
            st.rerun()

    st.divider()
    st.markdown('<div class="mmc-sidebar-label">Knowledge Base</div>', unsafe_allow_html=True)

    kb_sources = rag.list_sources()
    if kb_sources:
        for src in kb_sources:
            st.caption(f"📄 {src}")
    else:
        st.caption("No documents added yet — upload some to let the chatbot search them automatically.")

    if "kb_uploader_key" not in st.session_state:
        st.session_state.kb_uploader_key = 0

    kb_files = st.file_uploader(
        "Add documents",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=f"kb_uploader_{st.session_state.kb_uploader_key}",
    )
    if kb_files and st.button("Add to knowledge base", use_container_width=True):
        with st.spinner("Indexing documents..."):
            for f in kb_files:
                rag.add_document(f)
        st.session_state.kb_uploader_key += 1
        st.rerun()

    if kb_sources and st.button("Clear knowledge base", use_container_width=True):
        rag.clear()
        st.rerun()


# --- Brand mark ---
st.markdown(
    '<div class="mmc-brand"><div class="mmc-brand-mark">◆</div>'
    '<div class="mmc-brand-name">Multimodal Chatbot</div></div>',
    unsafe_allow_html=True,
)

# --- Empty-state greeting + clickable suggestion chips ---
if not active["display_history"]:
    st.markdown('<div class="mmc-greeting">What can I help with <span>today</span>?</div>', unsafe_allow_html=True)
    st.markdown('<div class="mmc-chip-row">', unsafe_allow_html=True)
    chip_cols = st.columns(2)
    for i, suggestion in enumerate(SUGGESTIONS):
        with chip_cols[i % 2]:
            if st.button(suggestion, key=f"chip_{i}", use_container_width=True):
                process_turn(active, suggestion)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- Replay past messages for the active conversation ---
for entry in active["display_history"]:
    render_message(
        entry["role"], entry["content"],
        entry.get("images"), entry.get("videos"), entry.get("attachment_name"),
    )

# --- Chat input with built-in paperclip attach icon, ChatGPT-style ---
prompt = st.chat_input(
    "Message the chatbot...",
    accept_file=True,
    file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "docx"],
)

if prompt and (prompt.text or prompt["files"]):
    uploaded_file = prompt["files"][0] if prompt["files"] else None
    process_turn(active, prompt.text or "", uploaded_file)
    st.rerun()