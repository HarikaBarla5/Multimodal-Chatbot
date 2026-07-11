"""
Multimodal Chatbot — Streamlit web app, "creative studio" theme.

Run locally with:  streamlit run app.py
Deploy for free on: https://share.streamlit.io (Streamlit Community Cloud)

This reuses the exact same text_gen.py, image_gen.py, video_gen.py, and
memory.py modules as the CLI version (main.py) — only the interface layer
is different, plus a custom CSS theme injected below.
"""

import streamlit as st
from config import validate_config
from memory import LongTermMemory
from text_gen import create_chat, get_response

st.set_page_config(page_title="Studio — Multimodal Chatbot", page_icon="🖋️", layout="centered")


# =========================================================================
# THEME — "creative studio" look: deep eggplant background, amber accent
# for the user, violet accent for the assistant, generated images shown
# as tilted polaroid frames (the signature element).
# =========================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

:root {
    --studio-bg: #1B1620;
    --studio-surface: #241E2B;
    --studio-surface-2: #2D2536;
    --studio-text: #F1EDE7;
    --studio-text-dim: #A79EB0;
    --studio-amber: #E8A33D;
    --studio-violet: #8C7AE6;
    --studio-border: #3A3245;
}

/* App background */
.stApp {
    background: var(--studio-bg);
    color: var(--studio-text);
}

/* Hide default Streamlit chrome that clashes with the theme */
#MainMenu, footer, header {visibility: hidden;}

/* ---- Header ---- */
.mmc-eyebrow {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--studio-amber);
    margin-bottom: 0.3rem;
}
.mmc-title {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 2.4rem;
    color: var(--studio-text);
    margin: 0 0 0.2rem 0;
    line-height: 1.1;
}
.mmc-subtitle {
    font-family: 'Inter', sans-serif;
    color: var(--studio-text-dim);
    font-size: 0.92rem;
    margin-bottom: 1.6rem;
}

/* ---- Chat bubbles (custom, not st.chat_message) ---- */
.mmc-row { display: flex; margin-bottom: 14px; }
.mmc-row.user { justify-content: flex-end; }
.mmc-row.assistant { justify-content: flex-start; }

.mmc-bubble {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    line-height: 1.5;
    padding: 12px 16px;
    border-radius: 14px;
    max-width: 78%;
    white-space: pre-wrap;
}
.mmc-bubble.user {
    background: var(--studio-amber);
    color: #211705;
    border-bottom-right-radius: 3px;
}
.mmc-bubble.assistant {
    background: var(--studio-surface);
    color: var(--studio-text);
    border: 1px solid var(--studio-border);
    border-left: 3px solid var(--studio-violet);
    border-bottom-left-radius: 3px;
}
.mmc-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--studio-text-dim);
    margin-bottom: 4px;
}

/* ---- Polaroid frame for generated images (the signature element) ---- */
.mmc-polaroid-wrap { display: flex; justify-content: flex-start; margin: 10px 0 18px 0; }
.mmc-polaroid {
    background: #FAF7F0;
    padding: 10px 10px 32px 10px;
    border-radius: 3px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.45);
    transform: rotate(-2deg);
    max-width: 260px;
}
.mmc-polaroid img {
    width: 100%;
    border-radius: 1px;
    display: block;
}
.mmc-polaroid-caption {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #4a4438;
    text-align: center;
    margin-top: 8px;
    letter-spacing: 0.03em;
}

/* ---- Sidebar restyled as an index-card drawer ---- */
[data-testid="stSidebar"] {
    background: var(--studio-surface);
    border-right: 1px solid var(--studio-border);
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    font-family: 'Fraunces', serif;
    color: var(--studio-text);
}
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] p {
    color: var(--studio-text-dim);
}
[data-testid="stSidebar"] .stTextInput input, [data-testid="stSidebar"] .stSelectbox div {
    background: var(--studio-surface-2);
    color: var(--studio-text);
    border: 1px solid var(--studio-border);
}
[data-testid="stSidebar"] .stButton button {
    background: var(--studio-amber);
    color: #211705;
    border: none;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    border-radius: 8px;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: #f0b155;
}

/* ---- Chat input bar ---- */
[data-testid="stChatInput"] {
    background: var(--studio-surface);
    border: 1px solid var(--studio-border);
    border-radius: 14px;
}
[data-testid="stChatInput"] textarea {
    color: var(--studio-text) !important;
    font-family: 'Inter', sans-serif;
}

/* ---- Divider ---- */
hr { border-color: var(--studio-border); }
</style>
""", unsafe_allow_html=True)


def build_system_prompt(long_term_memory: LongTermMemory) -> str:
    base = (
        "You are a helpful multimodal assistant. You can chat normally, and "
        "you can also generate images and videos when the user asks for them "
        "using the tools available to you."
    )
    memory_snippet = long_term_memory.as_system_prompt_snippet()
    if memory_snippet:
        return f"{base}\n\n{memory_snippet}"
    return base


def render_message(role: str, content: str, images=None):
    """Render one chat turn as a custom-styled bubble instead of the default st.chat_message."""
    label = "You" if role == "user" else "Studio"
    with st.container():
        st.markdown(
            f'<div class="mmc-row {role}">'
            f'<div class="mmc-bubble {role}">'
            f'<div class="mmc-label">{label}</div>{content}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        for img_path in (images or []):
            st.markdown('<div class="mmc-polaroid-wrap"><div class="mmc-polaroid">', unsafe_allow_html=True)
            st.image(img_path, use_container_width=True)
            st.markdown('<div class="mmc-polaroid-caption">developed just now</div></div></div>', unsafe_allow_html=True)


# --- One-time setup ---
try:
    validate_config()
except EnvironmentError as e:
    st.error(str(e))
    st.stop()

if "long_term_memory" not in st.session_state:
    st.session_state.long_term_memory = LongTermMemory()

if "chat" not in st.session_state:
    st.session_state.chat = create_chat(build_system_prompt(st.session_state.long_term_memory))

if "display_history" not in st.session_state:
    st.session_state.display_history = []


# --- Sidebar: long-term memory controls ---
with st.sidebar:
    st.markdown("### 🗂️ Memory drawer")
    facts = st.session_state.long_term_memory.facts

    if facts:
        for k, v in facts.items():
            st.markdown(f"**{k}**  \n{v}")
    else:
        st.caption("Nothing filed away yet.")

    st.divider()
    st.markdown("**Add a fact**")
    new_key = st.text_input("Key", key="new_key", placeholder="e.g. name", label_visibility="collapsed")
    new_value = st.text_input("Value", key="new_value", placeholder="e.g. Harika", label_visibility="collapsed")
    if st.button("Remember", use_container_width=True):
        if new_key and new_value:
            st.session_state.long_term_memory.remember(new_key.strip(), new_value.strip())
            st.session_state.chat = create_chat(
                build_system_prompt(st.session_state.long_term_memory)
            )
            st.rerun()

    if facts:
        st.divider()
        st.markdown("**Forget a fact**")
        forget_key = st.selectbox("Choose a key", options=list(facts.keys()), label_visibility="collapsed")
        if st.button("Forget", use_container_width=True):
            st.session_state.long_term_memory.forget(forget_key)
            st.session_state.chat = create_chat(
                build_system_prompt(st.session_state.long_term_memory)
            )
            st.rerun()


# --- Header ---
st.markdown('<div class="mmc-eyebrow">TEXT · IMAGE · VIDEO (SOON)</div>', unsafe_allow_html=True)
st.markdown('<div class="mmc-title">The Studio</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="mmc-subtitle">A quiet room that writes and paints on request — '
    'powered by Gemini and Pollinations.ai, free tier.</div>',
    unsafe_allow_html=True,
)

# --- Replay past messages ---
for entry in st.session_state.display_history:
    render_message(entry["role"], entry["content"], entry.get("images"))

# --- New user input ---
user_input = st.chat_input("Type a message, or ask for an image...")

if user_input:
    st.session_state.display_history.append({"role": "user", "content": user_input})
    render_message("user", user_input)

    with st.spinner("Working at the easel..."):
        reply, files = get_response(st.session_state.chat, user_input)

    render_message("assistant", reply, files)
    st.session_state.display_history.append(
        {"role": "assistant", "content": reply, "images": files}
    )