from collections import defaultdict
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.db.repository_supabase import create_run, list_runs
from app.db.supabase_store import SupabaseStore


def test_data_api_uses_server_key_and_returns_rows():
    client = Mock()
    client.get.return_value.is_error = False
    client.get.return_value.json.return_value = [{"id": "run-1"}]

    with patch(
        "app.db.supabase_store.get_settings",
        return_value=SimpleNamespace(
            SUPABASE_URL="https://project.example/rest/v1/",
            SUPABASE_SERVICE_ROLE_KEY="server-only-test-key",
        ),
    ), patch("app.db.supabase_store.httpx.Client", return_value=client) as make_client:
        store = SupabaseStore()
        rows = store.select("runs", {"owner_id": "user-1"})

    assert rows == [{"id": "run-1"}]
    assert make_client.call_args.kwargs["base_url"] == "https://project.example/rest/v1/"
    assert make_client.call_args.kwargs["headers"]["apikey"] == "server-only-test-key"
    assert make_client.call_args.kwargs["headers"]["Authorization"] == (
        "Bearer server-only-test-key"
    )
    client.get.assert_called_once_with(
        "runs", params=[("select", "*"), ("owner_id", "eq.user-1")]
    )


def test_data_api_surfaces_permission_errors():
    client = Mock()
    client.get.return_value.is_error = True
    client.get.return_value.status_code = 403
    store = SupabaseStore.__new__(SupabaseStore)
    store._client = client

    with pytest.raises(RuntimeError, match="HTTP 403"):
        store.select("runs")


class MemoryStore:
    def __init__(self):
        self.tables = defaultdict(list)
        self.next_id = defaultdict(int)

    def insert(self, table, values):
        row = dict(values)
        if table != "runs":
            self.next_id[table] += 1
            row.setdefault("id", self.next_id[table])
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        row.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        self.tables[table].append(row)
        return dict(row)

    def select(self, table, filters=None, order=None, limit=None, offset=None):
        rows = [
            row for row in self.tables[table]
            if all(row.get(key) == value for key, value in (filters or {}).items())
        ]
        if order:
            field, direction = order.split(".")
            rows.sort(key=lambda row: row.get(field), reverse=direction == "desc")
        rows = rows[offset or 0:]
        if limit is not None:
            rows = rows[:limit]
        return [dict(row) for row in rows]

    def update(self, table, filters, values):
        updated = []
        for row in self.tables[table]:
            if all(row.get(key) == value for key, value in filters.items()):
                row.update(values)
                updated.append(dict(row))
        return updated

    def delete(self, table, filters):
        self.tables[table] = [
            row for row in self.tables[table]
            if not all(row.get(key) == value for key, value in filters.items())
        ]


def test_data_api_repository_creates_run_with_source_and_event():
    store = MemoryStore()
    run = create_run(
        store,
        "run-1",
        "Operations",
        "Transcript",
        "Rules",
        owner_id="user-1",
    )

    assert run.status == "CREATED"
    assert run.owner_id == "user-1"
    assert store.tables["source_versions"][0]["transcript"] == "Transcript"
    assert store.tables["workflow_events"][0]["event_type"] == "run_created"


def test_data_api_repository_lists_only_runs_for_owner():
    store = MemoryStore()
    create_run(store, "run-1", "Owned", "T1", "R1", owner_id="user-1")
    create_run(store, "run-2", "Private", "T2", "R2", owner_id="user-2")

    runs = list_runs(store, "user-1")

    assert [run.id for run in runs] == ["run-1"]
