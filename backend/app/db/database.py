"""Persistence configuration for Supabase Data API and isolated tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.db.supabase_store import SupabaseStore


class Base(DeclarativeBase):
    """Declarative base for SQLite-only automated tests."""


_test_engine = None
_test_session_factory = None


def _test_database_url() -> str:
    return os.environ.get(
        "SQLITE_TEST_DATABASE_URL",
        "sqlite:///./test_data/test_operations.db",
    )


def _get_test_session_factory() -> sessionmaker:
    global _test_engine, _test_session_factory
    if _test_session_factory is None:
        url = make_url(_test_database_url())
        if url.drivername != "sqlite":
            raise ValueError("Automated test storage must use a local SQLite URL.")
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        _test_engine = create_engine(url, connect_args={"check_same_thread": False})
        _test_session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=_test_engine
        )
    return _test_session_factory


def get_session_factory() -> Callable[[], Any]:
    if os.environ.get("TESTING", "").lower() == "true":
        return _get_test_session_factory()
    return SupabaseStore


def get_db() -> Any:
    """Yield the configured persistence client for a request."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Validate runtime Data API configuration or initialize test tables."""
    global _test_engine
    if os.environ.get("TESTING", "").lower() == "true":
        from app.db import models  # noqa: F401 — registers test-only models
        factory = _get_test_session_factory()
        Base.metadata.create_all(bind=factory.kw["bind"])
        return

    store = SupabaseStore()
    store.close()


def reset_engine() -> None:
    """Reset cached SQLite-only test resources."""
    global _test_engine, _test_session_factory
    if _test_engine is not None:
        _test_engine.dispose()
    _test_engine = None
    _test_session_factory = None
