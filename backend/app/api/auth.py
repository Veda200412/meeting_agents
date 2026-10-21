"""Supabase Auth token verification for API requests."""

from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, str]:
    """Validate the access token with Supabase Auth and return its user ID."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to access this resource.")

    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured.")

    try:
        response = httpx.get(
            f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {credentials.credentials}",
            },
            timeout=10,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503, detail="Could not verify Supabase session."
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Supabase session is invalid or expired.")

    try:
        user = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="Supabase Auth returned an invalid response."
        ) from exc

    user_id = user.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=502, detail="Supabase Auth response has no user ID.")
    return {"id": user_id}
