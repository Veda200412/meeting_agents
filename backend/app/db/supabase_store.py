
"""Supabase Data API client for server-side workflow persistence."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings, supabase_project_url


class SupabaseStore:
    """Small synchronous PostgREST client; credentials remain server-side."""

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "to enable persistence."
            )

        service_key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()

        headers = {
            "apikey": service_key,
            "Content-Type": "application/json",
        }

        # New Supabase secret API keys are not JWTs.
        # Legacy service-role JWT keys use Bearer authorization.
        if not service_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {service_key}"

        self._client = httpx.Client(
            base_url=(
                f"{supabase_project_url(settings.SUPABASE_URL)}/rest/v1/"
            ),
            headers=headers,
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
            raise RuntimeError(
                f"Supabase Data API returned an invalid response for {table}."
            )

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
            raise RuntimeError(
                f"Supabase Data API did not return the inserted {table} row."
            )

        return rows[0]

    def update(
        self,
        table: str,
        filters: dict[str, Any],
        values: dict[str, Any],
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
            raise RuntimeError(
                f"Supabase Data API returned an invalid response for {table}."
            )

        return rows

    def delete(
        self,
        table: str,
        filters: dict[str, Any],
    ) -> None:
        params = self._filter_params(filters)
        response = self._client.delete(table, params=params)
        self._raise_for_error(response)

    def close(self) -> None:
        self._client.close()

    def commit(self) -> None:
        """Preserve the workflow interface; mutations commit per request."""

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        if response.is_error:
            message = (
                "Supabase Data API request failed with "
                f"HTTP {response.status_code}."
            )

            # Temporary diagnostics. Mocked responses may not have string
            # bodies, so only include details when response.text is a string.
            body = getattr(response, "text", "")
            if isinstance(body, str) and body:
                detail = body[:1000].replace("\n", " ")
                message += f" Response: {detail}"

            raise RuntimeError(message)

    @staticmethod
    def _filter_params(
        filters: dict[str, Any] | None,
    ) -> list[tuple[str, str]]:
        return [
            (key, "is.null" if value is None else f"eq.{value}")
            for key, value in (filters or {}).items()
        ]
