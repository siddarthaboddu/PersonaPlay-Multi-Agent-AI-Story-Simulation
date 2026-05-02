"""
Entry point for uvicorn.

Run with:
    uvicorn main:app --reload

Or from the new package directly:
    uvicorn app.main:app --reload
"""
from app.main import app  # noqa: F401
