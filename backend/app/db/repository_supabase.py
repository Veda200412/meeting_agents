"""Supabase Data API persistence operations scoped to run IDs."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from app.db.supabase_store import SupabaseStore


def _record(values: dict[str, Any] | None) -> SimpleNamespace | None:
    if values is not None:
        for key in ("created_at", "updated_at", "started_at", "completed_at"):
            value = values.get(key)
            if isinstance(value, str):
                values[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return SimpleNamespace(**values) if values is not None else None


def _rows(
    db: SupabaseStore,
    table: str,
    filters: dict[str, Any] | None = None,
    order: str | None = None,
) -> list[SimpleNamespace]:
    return [_record(row) for row in db.select(table, filters, order)]


def _one(
    db: SupabaseStore, table: str, filters: dict[str, Any]
) -> SimpleNamespace | None:
    rows = db.select(table, filters, limit=1)
    return _record(rows[0]) if rows else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run(
    db: SupabaseStore,
    run_id: str,
    name: str | None,
    transcript: str,
    company_rules: str,
    max_review_cycles: int = 2,
    owner_id: str | None = None,
) -> SimpleNamespace:
    run = _record(db.insert("runs", {
        "id": run_id,
        "name": name,
        "owner_id": owner_id,
        "status": "CREATED",
        "current_source_version": 1,
        "max_review_cycles": max_review_cycles,
        "review_cycle_count": 0,
    }))
    db.insert("source_versions", {
        "run_id": run_id,
        "version": 1,
        "transcript": transcript,
        "company_rules": company_rules,
    })
    add_event(
        db, run_id, "run_created", None, f"Run '{name or run_id}' created",
        {"source_version": 1},
    )
    return run


def get_run(db: SupabaseStore, run_id: str) -> SimpleNamespace | None:
    return _one(db, "runs", {"id": run_id})


def list_runs(
    db: SupabaseStore, owner_id: str, limit: int = 50, offset: int = 0
) -> list[SimpleNamespace]:
    rows = db.select(
        "runs", {"owner_id": owner_id}, order="created_at.desc",
        limit=limit, offset=offset,
    )
    return [_record(row) for row in rows]


def update_run_status(
    db: SupabaseStore, run_id: str, status: str, error_message: str | None = None
) -> None:
    db.update("runs", {"id": run_id}, {
        "status": status, "error_message": error_message, "updated_at": _now(),
    })


def set_run_fault(db: SupabaseStore, run_id: str, fault: str | None) -> None:
    db.update("runs", {"id": run_id}, {"fault_injection": fault})


def get_source_version(
    db: SupabaseStore, run_id: str, version: int
) -> SimpleNamespace | None:
    return _one(db, "source_versions", {"run_id": run_id, "version": version})


def get_current_source(db: SupabaseStore, run_id: str) -> SimpleNamespace | None:
    run = get_run(db, run_id)
    if not run:
        return None
    return get_source_version(db, run_id, run.current_source_version)


def create_source_version(
    db: SupabaseStore, run_id: str, version: int, transcript: str, company_rules: str
) -> SimpleNamespace:
    source = _record(db.insert("source_versions", {
        "run_id": run_id,
        "version": version,
        "transcript": transcript,
        "company_rules": company_rules,
    }))
    db.update("runs", {"id": run_id}, {
        "current_source_version": version, "updated_at": _now(),
    })
    return source


def save_facts(
    db: SupabaseStore, run_id: str, source_version: int, facts_data: list[dict]
) -> list[SimpleNamespace]:
    return [
        _record(db.insert("facts", {
            "run_id": run_id, "source_version": source_version, **fact,
        }))
        for fact in facts_data
    ]


def get_facts(
    db: SupabaseStore, run_id: str, source_version: int
) -> list[SimpleNamespace]:
    return _rows(db, "facts", {"run_id": run_id, "source_version": source_version})


def save_correction(
    db: SupabaseStore,
    run_id: str,
    fact_id: str,
    field_name: str,
    original_value: str | None,
    corrected_value: str,
    correction_note: str,
    new_source_version: int,
) -> SimpleNamespace:
    return _record(db.insert("user_corrections", {
        "run_id": run_id,
        "fact_id": fact_id,
        "field_name": field_name,
        "original_value": original_value,
        "corrected_value": corrected_value,
        "correction_note": correction_note,
        "new_source_version": new_source_version,
    }))


def get_corrections(db: SupabaseStore, run_id: str) -> list[SimpleNamespace]:
    return _rows(db, "user_corrections", {"run_id": run_id}, "created_at.asc")


def get_execution_by_step(
    db: SupabaseStore, step_id: str
) -> SimpleNamespace | None:
    return _one(db, "agent_executions", {"step_id": step_id})


def create_execution(
    db: SupabaseStore,
    run_id: str,
    agent_type: str,
    step_id: str,
    source_version: int,
    plan_version: int | None = None,
    attempt: int = 1,
    input_snapshot: dict | None = None,
) -> SimpleNamespace:
    existing = get_execution_by_step(db, step_id)
    now = _now()
    if existing:
        rows = db.update("agent_executions", {"step_id": step_id}, {
            "attempt_number": existing.attempt_number + 1,
            "status": "running",
            "started_at": now,
            "completed_at": None,
            "input_snapshot": input_snapshot,
            "output_snapshot": None,
            "error_message": None,
        })
        return _record(rows[0]) if rows else get_execution_by_step(db, step_id)
    return _record(db.insert("agent_executions", {
        "run_id": run_id,
        "agent_type": agent_type,
        "step_id": step_id,
        "attempt_number": attempt,
        "status": "running",
        "source_version": source_version,
        "plan_version": plan_version,
        "input_snapshot": input_snapshot,
    }))


def complete_execution(
    db: SupabaseStore,
    step_id: str,
    output_snapshot: dict | None = None,
    error: str | None = None,
) -> None:
    if get_execution_by_step(db, step_id):
        db.update("agent_executions", {"step_id": step_id}, {
            "status": "completed" if error is None else "failed",
            "completed_at": _now(),
            "output_snapshot": output_snapshot,
            "error_message": error,
        })


def get_executions(db: SupabaseStore, run_id: str) -> list[SimpleNamespace]:
    return _rows(db, "agent_executions", {"run_id": run_id}, "started_at.asc")


def get_completed_step(db: SupabaseStore, step_id: str) -> SimpleNamespace | None:
    return _one(db, "agent_executions", {"step_id": step_id, "status": "completed"})


def save_plan_version(
    db: SupabaseStore,
    run_id: str,
    version: int,
    source_version: int,
    plan_data: dict,
) -> SimpleNamespace:
    plan = _record(db.insert("plan_versions", {
        "run_id": run_id,
        "version": version,
        "source_version": source_version,
        "tasks": plan_data.get("tasks", []),
        "supported_facts": plan_data.get("supported_facts", []),
        "recommendations": plan_data.get("recommendations", []),
        "unresolved_questions": plan_data.get("unresolved_questions", []),
        "dependency_graph": plan_data.get("dependency_graph", []),
        "change_summary": plan_data.get("change_summary", []),
    }))
    db.update("runs", {"id": run_id}, {
        "current_plan_version": version, "updated_at": _now(),
    })
    return plan


def get_plan_version(
    db: SupabaseStore, run_id: str, version: int
) -> SimpleNamespace | None:
    return _one(db, "plan_versions", {"run_id": run_id, "version": version})


def get_current_plan(db: SupabaseStore, run_id: str) -> SimpleNamespace | None:
    run = get_run(db, run_id)
    if not run or not run.current_plan_version:
        return None
    return get_plan_version(db, run_id, run.current_plan_version)


def get_all_plans(db: SupabaseStore, run_id: str) -> list[SimpleNamespace]:
    return _rows(db, "plan_versions", {"run_id": run_id}, "version.asc")


def save_review_result(
    db: SupabaseStore,
    run_id: str,
    plan_version: int,
    source_version: int,
    outcome: str,
    findings: list[dict],
    summary: str,
    open_questions: list[str],
) -> SimpleNamespace:
    return _record(db.insert("review_results", {
        "run_id": run_id,
        "plan_version": plan_version,
        "source_version": source_version,
        "outcome": outcome,
        "findings": findings,
        "summary": summary,
        "open_questions": open_questions,
    }))


def get_review_for_plan(
    db: SupabaseStore, run_id: str, plan_version: int
) -> SimpleNamespace | None:
    return _one(db, "review_results", {"run_id": run_id, "plan_version": plan_version})


def get_all_reviews(db: SupabaseStore, run_id: str) -> list[SimpleNamespace]:
    return _rows(db, "review_results", {"run_id": run_id}, "created_at.asc")


def add_event(
    db: SupabaseStore,
    run_id: str,
    event_type: str,
    agent_type: str | None,
    description: str,
    version_info: dict | None = None,
) -> SimpleNamespace:
    return _record(db.insert("workflow_events", {
        "run_id": run_id,
        "event_type": event_type,
        "agent_type": agent_type,
        "description": description,
        "version_info": version_info,
    }))


def get_events(db: SupabaseStore, run_id: str) -> list[SimpleNamespace]:
    return _rows(db, "workflow_events", {"run_id": run_id}, "created_at.asc")


def save_handoff(
    db: SupabaseStore,
    run_id: str,
    from_agent: str,
    to_agent: str,
    payload_summary: str,
    source_version: int,
    plan_version: int | None = None,
    payload: dict | None = None,
) -> SimpleNamespace:
    filters = {
        "run_id": run_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "source_version": source_version,
        "plan_version": plan_version,
    }
    existing = _one(db, "handoff_records", filters)
    if existing:
        rows = db.update("handoff_records", {"id": existing.id}, {
            "payload_summary": payload_summary, "payload": payload,
        })
        return _record(rows[0]) if rows else existing
    return _record(db.insert("handoff_records", {
        **filters,
        "plan_version": plan_version,
        "payload_summary": payload_summary,
        "payload": payload,
    }))


def get_handoffs(db: SupabaseStore, run_id: str) -> list[SimpleNamespace]:
    return _rows(db, "handoff_records", {"run_id": run_id}, "created_at.asc")


def delete_run(db: SupabaseStore, run_id: str) -> bool:
    if not get_run(db, run_id):
        return False
    db.delete("runs", {"id": run_id})
    return True


def invalidate_downstream(db: SupabaseStore, run_id: str) -> None:
    for table in (
        "review_results", "plan_versions", "agent_executions",
        "facts", "handoff_records",
    ):
        db.delete(table, {"run_id": run_id})
    db.update("runs", {"id": run_id}, {
        "current_plan_version": None,
        "review_cycle_count": 0,
        "status": "CREATED",
        "error_message": None,
    })
