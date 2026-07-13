"""
Handles files the user uploads (images, PDFs, text, Word docs) so they can
be included in a message sent to Gemini.

Gemini's API natively understands images and PDFs as raw binary data — the
model can literally "see" a photo or "read" a PDF's pages directly, no
extraction needed. Plain text and Word documents aren't natively
understood as binary by Gemini, so for those we extract the text
ourselves and fold it into the message.
"""

import io
from google.genai import types

NATIVE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def get_extension(filename: str) -> str:
    filename = filename.lower()
    return "." + filename.split(".")[-1] if "." in filename else ""


def build_message_content(user_text: str, uploaded_file):
    """
    Given the user's typed text and an uploaded Streamlit file object (or
    None), returns what to pass to chat.send_message() — either a plain
    string (no attachment) or a list mixing text with a file Part
    (image/PDF) or extracted text (txt/docx).
    """
    if uploaded_file is None:
        return user_text

    extension = get_extension(uploaded_file.name)
    file_bytes = uploaded_file.getvalue()

    if extension in NATIVE_MIME_TYPES:
        mime_type = NATIVE_MIME_TYPES[extension]
        return [
            user_text,
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
        ]

    if extension == ".txt":
        text_content = file_bytes.decode("utf-8", errors="replace")
        return (
            f"{user_text}\n\n--- Attached file: {uploaded_file.name} ---\n"
            f"{text_content}"
        )

    if extension == ".docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            text_content = "\n".join(p.text for p in doc.paragraphs)
            return (
                f"{user_text}\n\n--- Attached file: {uploaded_file.name} ---\n"
                f"{text_content}"
            )
        except ImportError:
            return (
                f"{user_text}\n\n[Attached file {uploaded_file.name} couldn't "
                f"be read — the python-docx package isn't installed.]"
            )

    return (
        f"{user_text}\n\n[Attached file {uploaded_file.name} has an "
        f"unsupported format and was not included.]"
    )