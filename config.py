"""
Configuration for the multimodal chatbot.

Reads the Gemini API key from one of two places, in this order:
    1. Streamlit secrets (used automatically when deployed on Streamlit
       Community Cloud — see .streamlit/secrets.toml)
    2. The GEMINI_API_KEY environment variable (used for local development)

Never hardcode your real key directly in this file if you plan to push
this project to GitHub — use one of the two methods above instead.

Local setup (Mac/Linux):
    export GEMINI_API_KEY="AIza..."
Local setup (Windows PowerShell):
    setx GEMINI_API_KEY "AIza..."   (then restart your terminal)

Streamlit Cloud setup:
    In your app's dashboard -> Settings -> Secrets, add:
        GEMINI_API_KEY = "AIza..."
"""

import os

try:
    import streamlit as st
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
except Exception:
    # Not running inside Streamlit (e.g. plain `python main.py`) — fall
    # back to the environment variable only.
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.5-flash"  # current free-tier flagship Flash model

# Where generated images are saved locally
IMAGE_OUTPUT_DIR = "generated_images"

# Memory files
LONG_TERM_MEMORY_FILE = "long_term_memory.json"


def validate_config():
    if not GEMINI_API_KEY:
        raise EnvironmentError(
            "Missing GEMINI_API_KEY. Set it as an environment variable "
            "locally, or as a Streamlit secret when deployed. "
            "See the top of config.py for instructions."
        )