"""Uvicorn entry point: uvicorn api:app --reload"""

from classroom_ai.api import app

__all__ = ["app"]
