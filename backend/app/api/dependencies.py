"""FastAPI dependencies."""

from app.db.database import get_db


# Re-export for clean imports in routes
__all__ = ["get_db"]
