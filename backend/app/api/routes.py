"""
REST API routes (non-WebSocket operations).
"""
from fastapi import APIRouter

from app.agents.beats import beats_as_json

router = APIRouter(prefix="/api")


@router.get("/beats")
def get_beats():
    """
    Returns the canonical narrative beat map.
    The frontend should consume this to stay in sync with the backend
    instead of maintaining a duplicate JS copy.
    """
    return beats_as_json()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "PersonaPlay Pro"}
