"""
Image generation via Pollinations.ai — a free, no-API-key image generation
service. Just build a URL with the prompt and download the resulting image.

No account, no key, no billing. Great for prototyping; if you outgrow it
later, this is the file to swap for a different provider (Stability AI,
OpenAI, etc.) — the rest of the app doesn't need to change.
"""

import os
import time
import urllib.parse
import requests
from config import IMAGE_OUTPUT_DIR

POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt/"


def generate_image(prompt: str) -> str:
    """
    Generate an image from a text prompt.
    Returns the local file path of the saved PNG, or an error message string.
    """
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url =f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=300&height=300"
        response = requests.get(url, timeout=100)
        response.raise_for_status()
        filename = f"image_{int(time.time())}.png"
        filepath = os.path.join(IMAGE_OUTPUT_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

        return filepath

    except Exception as e:
        return f"[Image generation failed: {e}]"