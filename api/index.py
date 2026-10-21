"""Vercel Python function entry point for the FastAPI application."""

from pathlib import Path
import sys

backend_path = str(Path(__file__).resolve().parents[1] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
