"""Tests for the image service."""
from app.models.state import Prop, WorldState
from app.services.image import build_scene_image_url


def _world(location="Test Room", lighting="Dim", props=None) -> WorldState:
    return WorldState(
        location=location,
        lighting=lighting,
        props=props or [],
    )


def test_url_contains_location():
    url, prompt = build_scene_image_url(_world(location="The Library"))
    assert "The%20Library" in url or "Library" in prompt


def test_prompt_contains_lighting():
    _, prompt = build_scene_image_url(_world(lighting="Moonlight"))
    assert "Moonlight" in prompt


def test_only_visible_props_in_prompt():
    props = [
        Prop(id="secret_letter", owner="Alice", visibility="hidden"),
        Prop(id="candle", owner="Nobody", visibility="visible"),
    ]
    _, prompt = build_scene_image_url(_world(props=props))
    assert "candle" in prompt
    assert "secret letter" not in prompt


def test_deterministic_with_fixed_seed():
    world = _world()
    url1, _ = build_scene_image_url(world, seed=42)
    url2, _ = build_scene_image_url(world, seed=42)
    assert url1 == url2


def test_different_seeds_produce_different_urls():
    world = _world()
    url1, _ = build_scene_image_url(world, seed=1)
    url2, _ = build_scene_image_url(world, seed=2)
    assert url1 != url2
