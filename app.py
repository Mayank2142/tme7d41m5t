"""Recognized Vercel FastAPI entry point; shares the local application factory."""

from backend.app.main import create_app

app = create_app()
