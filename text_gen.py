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

# Tracks files generated during the current turn, so main.py can show them.
# Reset at the start of every get_response() call.
_last_generated_files = []


def generate_image(prompt: str) -> str:
    """Generate an image from a text description and save it locally.

    Args:
        prompt: A detailed description of the image to generate.

    Returns:
        The local file path where the generated image was saved.
    """
    result = _generate_image_impl(prompt)
    if not result.startswith("["):
        _last_generated_files.append(result)
    return result


def generate_video(prompt: str) -> str:
    """Generate a short video from a text description.

    Args:
        prompt: A detailed description of the video to generate.

    Returns:
        A status message (video generation is not wired up to a real
        provider yet — see video_gen.py).
    """
    return _generate_video_impl(prompt)


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


def get_response(chat, user_message: str):
    """
    Sends one message to an existing chat session and returns
    (reply_text, list_of_generated_file_paths).
    """
    global _last_generated_files
    _last_generated_files = []

    response = chat.send_message(user_message)

    return response.text, list(_last_generated_files)