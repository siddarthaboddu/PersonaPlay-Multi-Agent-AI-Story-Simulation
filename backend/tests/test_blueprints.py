"""Tests for starting blueprints catalog and REST API."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.constants.blueprints import STARTING_BLUEPRINTS, get_starting_blueprints


def test_blueprints_catalog_structure():
    """Verify all blueprints have necessary theatrical attributes."""
    blueprints = get_starting_blueprints()
    assert len(blueprints) >= 5, "Expected at least 5 starter blueprints"

    for bp in blueprints:
        assert "id" in bp and len(bp["id"]) > 0
        assert "title" in bp and len(bp["title"]) > 0
        assert "genre" in bp and len(bp["genre"]) > 0
        assert "scene" in bp
        assert "name" in bp["scene"]
        assert "location" in bp["scene"]
        assert "lighting" in bp["scene"]
        assert "props" in bp and isinstance(bp["props"], list)
        assert len(bp["props"]) >= 1
        assert "agents" in bp and isinstance(bp["agents"], list)
        assert len(bp["agents"]) >= 2

        # Check agent structure
        for ag in bp["agents"]:
            assert "id" in ag
            assert "traits" in ag
            assert "hidden_agenda" in ag
            assert "emotions" in ag
            assert "relationships" in ag


def test_blueprints_api_endpoint():
    """Verify GET /api/blueprints returns 200 OK and valid JSON data."""
    client = TestClient(app)
    response = client.get("/api/blueprints")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(STARTING_BLUEPRINTS)
    ids = [b["id"] for b in data]
    assert "cozy_living_room" in ids
    assert "first_apartment_unpacking" in ids
    assert "midnight_kitchen_pancakes" in ids
    assert "corner_cafe_study" in ids
    assert "road_trip_aux_war" in ids
    assert "game_night_rivalry" in ids

