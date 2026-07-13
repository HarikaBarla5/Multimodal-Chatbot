"""
Video generation via deAPI.ai's image-to-video endpoint.

deAPI's video models animate a starting IMAGE rather than working from
pure text — so this module does a two-step pipeline:
    1. Generate a starting frame using our existing free image_gen.py
       (Pollinations.ai), described by the user's prompt.
    2. Send that image + the prompt to deAPI's img2video endpoint, which
       animates it into a short clip.

This means "video generation" here really means "animate an AI-generated
image based on your description" — a reasonable free approximation of
true text-to-video, which has no reliable free equivalent right now.

IMPORTANT — this integration was built from deAPI's public docs/playground
without live testing against a real account. The submit step (POST to
img2video) is confirmed and documented. The exact shape of an in-progress
job response (what field holds the job ID, what the polling endpoint is)
was NOT fully confirmed from docs alone, since deAPI's video jobs are
asynchronous. This code makes a reasonable attempt at handling that, but
if it doesn't work first try, print(response.json()) at the marked spot
below to see the real response shape and adjust from there.
"""

import os
import time
import requests
from config import DEAPI_API_KEY, IMAGE_OUTPUT_DIR
from image_gen import generate_image

DEAPI_IMG2VIDEO_URL = "https://api.deapi.ai/api/v1/client/img2video"
VIDEO_OUTPUT_DIR = "generated_videos"

# Reasonable default model based on deAPI's documented playground example.
# Check https://docs.deapi.ai/models for the current list if this stops
# working — model slugs on these platforms change over time.
DEAPI_MODEL = "Ltx2_3_22B_Dist_INT8"


def generate_video(prompt: str) -> str:
    """
    Generate a short video from a text prompt by first creating a still
    image (via Pollinations.ai), then animating it (via deAPI.ai).

    Returns the local file path of the saved MP4, or an error message
    string starting with "[" if anything failed.
    """
    if not DEAPI_API_KEY:
        return (
            "[Video generation needs a deAPI key. Sign up free at "
            "app.deapi.ai/register and set DEAPI_API_KEY — see config.py.]"
        )

    # --- Step 1: generate the starting frame (reuses existing free path) ---
    image_path = generate_image(prompt)
    if image_path.startswith("["):
        return f"[Video generation failed at the image step: {image_path}]"

    os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)

    try:
        with open(image_path, "rb") as image_file:
            response = requests.post(
                DEAPI_IMG2VIDEO_URL,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {DEAPI_API_KEY}",
                },
                files={"first_frame_image": image_file},
                data={
                    "prompt": prompt,
                    "model": DEAPI_MODEL,
                    "width": "512",
                    "height": "512",
                    "frames": "120",
                    "fps": "24",
                },
                timeout=120,
            )

        response.raise_for_status()
        result = response.json()

        # --- DEBUGGING AID ---
        # Uncomment this line on your first real test to see exactly what
        # deAPI sends back, then adjust the parsing below to match:
        # print("DEAPI RESPONSE:", result)

        video_url = _extract_video_url(result)

        # If we didn't get a direct URL, this may be an async job that
        # needs polling. deAPI's exact polling endpoint wasn't confirmed
        # from docs alone — if this branch triggers, check the printed
        # response above and see docs.deapi.ai for the current job-status
        # endpoint, then update _poll_for_video() below.
        if not video_url and "id" in result:
            video_url = _poll_for_video(result["id"])

        if not video_url:
            return f"[Video generation: unexpected response shape from deAPI: {result}]"

        video_response = requests.get(video_url, timeout=120)
        video_response.raise_for_status()

        filename = f"video_{int(time.time())}.mp4"
        filepath = os.path.join(VIDEO_OUTPUT_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(video_response.content)

        return filepath

    except Exception as e:
        return f"[Video generation failed: {e}]"


def _extract_video_url(result: dict):
    """Try a few common response shapes to find a direct video URL."""
    for key in ("video_url", "url", "output_url"):
        if key in result:
            return result[key]
    if "output" in result and isinstance(result["output"], dict):
        return result["output"].get("url") or result["output"].get("video_url")
    if "data" in result and isinstance(result["data"], dict):
        return result["data"].get("url") or result["data"].get("video_url")
    return None


def _poll_for_video(job_id: str, max_wait_seconds: int = 180, interval_seconds: int = 10):
    """
    Best-effort polling for an async video job. The exact status endpoint
    was not confirmed from deAPI's public docs — this assumes a common
    REST pattern. If it 404s, check docs.deapi.ai for the real endpoint
    and update DEAPI_STATUS_URL_TEMPLATE below.
    """
    DEAPI_STATUS_URL_TEMPLATE = "https://api.deapi.ai/api/v1/client/jobs/{job_id}"
    waited = 0

    while waited < max_wait_seconds:
        time.sleep(interval_seconds)
        waited += interval_seconds

        try:
            status_response = requests.get(
                DEAPI_STATUS_URL_TEMPLATE.format(job_id=job_id),
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {DEAPI_API_KEY}",
                },
                timeout=30,
            )
            status_response.raise_for_status()
            status_result = status_response.json()
        except Exception:
            continue  # transient error, keep trying until max_wait_seconds

        video_url = _extract_video_url(status_result)
        if video_url:
            return video_url

        if status_result.get("status") == "failed":
            return None

    return None