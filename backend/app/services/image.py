"""
Image generation service using Pollinations AI (keyless, open-source friendly).
Extracted from the director_command handler so it can be tested/replaced independently.
"""
import random
import urllib.parse

from app.models.state import WorldState


def build_scene_image_url(world_state: WorldState, seed: int | None = None) -> tuple[str, str]:
    """
    Generate a Pollinations AI image URL for the current world state.

    Returns:
        (url, prompt) tuple — the frontend renders the url and displays the prompt.
    """
    if seed is None:
        seed = random.randint(1, 100_000)

    props_str = ", ".join(
        p.id.replace("_", " ")
        for p in world_state.props
        if p.visibility == "visible"
    )
    prompt = (
        f"Cinematic movie still, {world_state.lighting} lighting, "
        f"{world_state.location}. "
        f"Visible props: {props_str}. "
        f"Dramatic, 8k resolution, highly detailed."
    )
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=800&height=400&nologo=true&seed={seed}"
    )
    return url, prompt
