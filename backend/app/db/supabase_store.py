"""Supabase Data API client for server-side workflow persistence."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class SupabaseStore:
    """Small synchronous PostgREST client; credentials remain server-side."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable persistence."
            )
        self._client = httpx.Client(
            base_url=f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/",
            headers={
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    def select(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        params: list[tuple[str, str]] = [("select", "*")]
        params.extend(self._filter_params(filters))
        if order:
            params.append(("order", order))
        if limit is not None:
            params.append(("limit", str(limit)))
        if offset is not None:
            params.append(("offset", str(offset)))
        response = self._client.get(table, params=params)
        self._raise_for_error(response)
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Supabase Data API returned an invalid response for {table}.")
        return data

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(
            table,
            json=values,
            headers={"Prefer": "return=representation"},
        )
        self._raise_for_error(response)
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise RuntimeError(f"Supabase Data API did not return the inserted {table} row.")
        return rows[0]

    def update(
        self, table: str, filters: dict[str, Any], values: dict[str, Any]
    ) -> list[dict[str, Any]]:
        params = self._filter_params(filters)
        response = self._client.patch(
            table,
            params=params,
            json=values,
            headers={"Prefer": "return=representation"},
        )
        self._raise_for_error(response)
        rows = response.json()
        if not isinstance(rows, list):
            raise RuntimeError(f"Supabase Data API returned an invalid response for {table}.")
        return rows

    def delete(self, table: str, filters: dict[str, Any]) -> None:
        params = self._filter_params(filters)
        response = self._client.delete(table, params=params)
        self._raise_for_error(response)

    def close(self) -> None:
        self._client.close()

    def commit(self) -> None:
        """Preserve the workflow interface; Data API mutations commit per request."""

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        if response.is_error:
            raise RuntimeError(
                f"Supabase Data API request failed with HTTP {response.status_code}."
            )

    @staticmethod
    def _filter_params(filters: dict[str, Any] | None) -> list[tuple[str, str]]:
        return [
            (key, "is.null" if value is None else f"eq.{value}")
            for key, value in (filters or {}).items()
        ]
