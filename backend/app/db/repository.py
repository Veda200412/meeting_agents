"""Repository entry points for Supabase runtime and isolated SQLite tests."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db import repository_sqlite, repository_supabase
from app.db.supabase_store import SupabaseStore


def __getattr__(name: str) -> Callable[..., Any]:
    supabase_operation = getattr(repository_supabase, name, None)
    sqlite_operation = getattr(repository_sqlite, name, None)
    if supabase_operation is None or sqlite_operation is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    @wraps(supabase_operation)
    def dispatch(db: SupabaseStore | Session, *args: Any, **kwargs: Any) -> Any:
        operation = sqlite_operation if isinstance(db, Session) else supabase_operation
        return operation(db, *args, **kwargs)

    return dispatch
