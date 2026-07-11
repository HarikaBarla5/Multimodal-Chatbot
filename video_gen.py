"""
Video generation — placeholder module.

Video APIs (Runway, Luma Dream Machine, etc.) are async: you submit a job,
poll for completion, then download the result. Once you pick a provider,
replace the body of generate_video() with real API calls following that
same submit -> poll -> download pattern.
"""


def generate_video(prompt: str) -> str:
    """
    Stub for video generation. Replace this with a real API call once
    you've chosen a provider (Runway ML, Luma AI, Stability AI, etc.)
    """
    return (
        "[Video generation isn't wired up yet. "
        f"Would have generated a video for: '{prompt}'. "
        "See video_gen.py for where to plug in a real provider.]"
    )