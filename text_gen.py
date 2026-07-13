"""
Core chat logic using Google's Gemini API with automatic function calling.

Gemini's SDK supports passing real Python functions as "tools." When Gemini
decides a tool is needed (e.g. the user asked for an image), the SDK calls
that Python function for you automatically and feeds the result back to
the model — no manual tool-call loop required. This is different from the
Claude/OpenAI pattern where you handle the tool_use step yourself.

Each function's docstring and type hints are read by Gemini to understand
what the tool does and what arguments it needs, so keep them accurate.
"""

from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL
from image_gen import generate_image as _generate_image_impl
from video_gen import generate_video as _generate_video_impl

client = genai.Client(api_key=GEMINI_API_KEY)

# Tracks files generated during the current turn, so the interface layer
# (app.py / main.py) can display them. Reset at the start of every
# get_response() call. Images and videos are tracked separately since
# they're displayed differently in the UI.
_last_generated_images = []
_last_generated_videos = []


def generate_image(prompt: str) -> str:
    """Generate an image from a text description and save it locally.

    Args:
        prompt: A detailed description of the image to generate.

    Returns:
        The local file path where the generated image was saved.
    """
    result = _generate_image_impl(prompt)
    if not result.startswith("["):
        _last_generated_images.append(result)
    return result


def generate_video(prompt: str) -> str:
    """Generate a short video from a text description.

    Args:
        prompt: A detailed description of the video to generate.

    Returns:
        The local file path where the generated video was saved, or an
        error message if video generation isn't configured/available.
    """
    result = _generate_video_impl(prompt)
    if not result.startswith("["):
        _last_generated_videos.append(result)
    return result


def create_chat(system_prompt: str):
    """
    Creates a new Gemini chat session. The session keeps its own
    conversation history internally, so you don't need to manage a
    message list by hand — just keep calling send on the same session.
    """
    return client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[generate_image, generate_video],
        ),
    )


def get_response(chat, content):
    """
    Sends one message to an existing chat session and returns
    (reply_text, list_of_generated_image_paths, list_of_generated_video_paths).

    `content` can be a plain string (text-only message) or a list mixing
    text with a file Part (see file_handler.build_message_content) —
    Gemini's SDK accepts both.
    """
    global _last_generated_images, _last_generated_videos
    _last_generated_images = []
    _last_generated_videos = []

    response = chat.send_message(content)

    return response.text, list(_last_generated_images), list(_last_generated_videos)