"""SQLite repository used only by the isolated automated test harness."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import (
    Run, SourceVersion, Fact, UserCorrection,
    AgentExecution, PlanVersion, ReviewResult,
    WorkflowEvent, HandoffRecord,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Runs ──────────────────────────────────────────────

def create_run(db: Session, run_id: str, name: Optional[str],
               transcript: str, company_rules: str,
               max_review_cycles: int = 2,
               owner_id: str | None = None) -> Run:
    run = Run(
        id=run_id, name=name, owner_id=owner_id, status="CREATED",
        current_source_version=1, max_review_cycles=max_review_cycles,
    )
    db.add(run)
    sv = SourceVersion(
        run_id=run_id, version=1,
        transcript=transcript, company_rules=company_rules,
    )
    db.add(sv)
    add_event(db, run_id, "run_created", None,
              f"Run '{name or run_id}' created", {"source_version": 1})
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: str) -> Optional[Run]:
    return db.query(Run).filter(Run.id == run_id).first()


def list_runs(db: Session, owner_id: str, limit: int = 50, offset: int = 0) -> list[Run]:
    return (db.query(Run)
            .filter(Run.owner_id == owner_id)
            .order_by(Run.created_at.desc())
            .offset(offset).limit(limit).all())


def update_run_status(db: Session, run_id: str, status: str,
                      error_message: str | None = None) -> None:
    run = get_run(db, run_id)
    if run:
        run.status = status
        run.error_message = error_message
        run.updated_at = _utcnow()
        db.commit()


def set_run_fault(db: Session, run_id: str, fault: str | None) -> None:
    run = get_run(db, run_id)
    if run:
        run.fault_injection = fault
        db.commit()


# ── Source Versions ───────────────────────────────────

def get_source_version(db: Session, run_id: str, version: int) -> Optional[SourceVersion]:
    return (db.query(SourceVersion)
            .filter(SourceVersion.run_id == run_id,
                    SourceVersion.version == version)
            .first())


def get_current_source(db: Session, run_id: str) -> Optional[SourceVersion]:
    run = get_run(db, run_id)
    if not run:
        return None
    return get_source_version(db, run_id, run.current_source_version)


def create_source_version(db: Session, run_id: str, version: int,
                          transcript: str, company_rules: str) -> SourceVersion:
    sv = SourceVersion(
        run_id=run_id, version=version,
        transcript=transcript, company_rules=company_rules,
    )
    db.add(sv)
    run = get_run(db, run_id)
    if run:
        run.current_source_version = version
        run.updated_at = _utcnow()
    db.commit()
    db.refresh(sv)
    return sv


# ── Facts ─────────────────────────────────────────────

def save_facts(db: Session, run_id: str, source_version: int,
               facts_data: list[dict]) -> list[Fact]:
    facts = []
    for fd in facts_data:
        f = Fact(run_id=run_id, source_version=source_version, **fd)
        db.add(f)
        facts.append(f)
    db.commit()
    return facts


def get_facts(db: Session, run_id: str, source_version: int) -> list[Fact]:
    return (db.query(Fact)
            .filter(Fact.run_id == run_id,
                    Fact.source_version == source_version)
            .all())


# ── User Corrections ─────────────────────────────────

def save_correction(db: Session, run_id: str, fact_id: str,
                    field_name: str, original_value: str | None,
                    corrected_value: str, correction_note: str,
                    new_source_version: int) -> UserCorrection:
    uc = UserCorrection(
        run_id=run_id, fact_id=fact_id, field_name=field_name,
        original_value=original_value, corrected_value=corrected_value,
        correction_note=correction_note,
        new_source_version=new_source_version,
    )
    db.add(uc)
    db.commit()
    db.refresh(uc)
    return uc


def get_corrections(db: Session, run_id: str) -> list[UserCorrection]:
    return (db.query(UserCorrection)
            .filter(UserCorrection.run_id == run_id)
            .order_by(UserCorrection.created_at).all())


# ── Agent Executions ──────────────────────────────────

def get_execution_by_step(db: Session, step_id: str) -> Optional[AgentExecution]:
    return db.query(AgentExecution).filter(AgentExecution.step_id == step_id).first()


def create_execution(db: Session, run_id: str, agent_type: str,
                     step_id: str, source_version: int,
                     plan_version: int | None = None,
                     attempt: int = 1,
                     input_snapshot: dict | None = None) -> AgentExecution:
    existing = get_execution_by_step(db, step_id)
    if existing:
        existing.attempt_number += 1
        existing.status = "running"
        existing.started_at = _utcnow()
        existing.completed_at = None
        existing.input_snapshot = input_snapshot
        existing.output_snapshot = None
        existing.error_message = None
        db.commit()
        db.refresh(existing)
        return existing

    ae = AgentExecution(
        run_id=run_id, agent_type=agent_type, step_id=step_id,
        attempt_number=attempt, status="running",
        source_version=source_version, plan_version=plan_version,
        input_snapshot=input_snapshot,
    )
    db.add(ae)
    db.commit()
    db.refresh(ae)
    return ae


def complete_execution(db: Session, step_id: str,
                       output_snapshot: dict | None = None,
                       error: str | None = None) -> None:
    ae = get_execution_by_step(db, step_id)
    if ae:
        ae.status = "completed" if error is None else "failed"
        ae.completed_at = _utcnow()
        ae.output_snapshot = output_snapshot
        ae.error_message = error
        db.commit()


def get_executions(db: Session, run_id: str) -> list[AgentExecution]:
    return (db.query(AgentExecution)
            .filter(AgentExecution.run_id == run_id)
            .order_by(AgentExecution.started_at).all())


def get_completed_step(db: Session, step_id: str) -> Optional[AgentExecution]:
    return (db.query(AgentExecution)
            .filter(AgentExecution.step_id == step_id,
                    AgentExecution.status == "completed")
            .first())


# ── Plan Versions ─────────────────────────────────────

def save_plan_version(db: Session, run_id: str, version: int,
                      source_version: int, plan_data: dict) -> PlanVersion:
    pv = PlanVersion(
        run_id=run_id, version=version, source_version=source_version,
        tasks=plan_data.get("tasks", []),
        supported_facts=plan_data.get("supported_facts", []),
        recommendations=plan_data.get("recommendations", []),
        unresolved_questions=plan_data.get("unresolved_questions", []),
        dependency_graph=plan_data.get("dependency_graph", []),
        change_summary=plan_data.get("change_summary", []),
    )
    db.add(pv)
    run = get_run(db, run_id)
    if run:
        run.current_plan_version = version
    db.commit()
    db.refresh(pv)
    return pv


def get_plan_version(db: Session, run_id: str, version: int) -> Optional[PlanVersion]:
    return (db.query(PlanVersion)
            .filter(PlanVersion.run_id == run_id,
                    PlanVersion.version == version)
            .first())


def get_current_plan(db: Session, run_id: str) -> Optional[PlanVersion]:
    run = get_run(db, run_id)
    if not run or not run.current_plan_version:
        return None
    return get_plan_version(db, run_id, run.current_plan_version)


def get_all_plans(db: Session, run_id: str) -> list[PlanVersion]:
    return (db.query(PlanVersion)
            .filter(PlanVersion.run_id == run_id)
            .order_by(PlanVersion.version).all())


# ── Review Results ────────────────────────────────────

def save_review_result(db: Session, run_id: str, plan_version: int,
                       source_version: int, outcome: str,
                       findings: list[dict], summary: str,
                       open_questions: list[str]) -> ReviewResult:
    rr = ReviewResult(
        run_id=run_id, plan_version=plan_version,
        source_version=source_version, outcome=outcome,
        findings=findings, summary=summary,
        open_questions=open_questions,
    )
    db.add(rr)
    db.commit()
    db.refresh(rr)
    return rr


def get_review_for_plan(db: Session, run_id: str,
                        plan_version: int) -> Optional[ReviewResult]:
    return (db.query(ReviewResult)
            .filter(ReviewResult.run_id == run_id,
                    ReviewResult.plan_version == plan_version)
            .first())


def get_all_reviews(db: Session, run_id: str) -> list[ReviewResult]:
    return (db.query(ReviewResult)
            .filter(ReviewResult.run_id == run_id)
            .order_by(ReviewResult.created_at).all())


# ── Workflow Events ───────────────────────────────────

def add_event(db: Session, run_id: str, event_type: str,
              agent_type: str | None, description: str,
              version_info: dict | None = None) -> WorkflowEvent:
    ev = WorkflowEvent(
        run_id=run_id, event_type=event_type,
        agent_type=agent_type, description=description,
        version_info=version_info,
    )
    db.add(ev)
    # Don't commit here; caller decides
    return ev


def get_events(db: Session, run_id: str) -> list[WorkflowEvent]:
    return (db.query(WorkflowEvent)
            .filter(WorkflowEvent.run_id == run_id)
            .order_by(WorkflowEvent.created_at).all())


# ── Handoff Records ──────────────────────────────────

def save_handoff(db: Session, run_id: str, from_agent: str,
                 to_agent: str, payload_summary: str,
                 source_version: int,
                 plan_version: int | None = None,
                 payload: dict | None = None) -> HandoffRecord:
    existing = (db.query(HandoffRecord)
                .filter(
                    HandoffRecord.run_id == run_id,
                    HandoffRecord.from_agent == from_agent,
                    HandoffRecord.to_agent == to_agent,
                    HandoffRecord.source_version == source_version,
                    HandoffRecord.plan_version == plan_version,
                )
                .first())
    if existing:
        if payload is not None:
            existing.payload_summary = payload_summary
            existing.payload = payload
            db.commit()
            db.refresh(existing)
        return existing

    hr = HandoffRecord(
        run_id=run_id, from_agent=from_agent, to_agent=to_agent,
        payload_summary=payload_summary,
        payload=payload,
        source_version=source_version, plan_version=plan_version,
    )
    db.add(hr)
    db.commit()
    db.refresh(hr)
    return hr


def get_handoffs(db: Session, run_id: str) -> list[HandoffRecord]:
    return (db.query(HandoffRecord)
            .filter(HandoffRecord.run_id == run_id)
            .order_by(HandoffRecord.created_at).all())


# ── Cleanup / Reset ──────────────────────────────────

def delete_run(db: Session, run_id: str) -> bool:
    run = get_run(db, run_id)
    if not run:
        return False
    # Delete in dependency order
    db.query(WorkflowEvent).filter(WorkflowEvent.run_id == run_id).delete()
    db.query(HandoffRecord).filter(HandoffRecord.run_id == run_id).delete()
    db.query(ReviewResult).filter(ReviewResult.run_id == run_id).delete()
    db.query(PlanVersion).filter(PlanVersion.run_id == run_id).delete()
    db.query(AgentExecution).filter(AgentExecution.run_id == run_id).delete()
    db.query(UserCorrection).filter(UserCorrection.run_id == run_id).delete()
    db.query(Fact).filter(Fact.run_id == run_id).delete()
    db.query(SourceVersion).filter(SourceVersion.run_id == run_id).delete()
    db.delete(run)
    db.commit()
    return True


def invalidate_downstream(db: Session, run_id: str) -> None:
    """Invalidate all downstream outputs after a source change.

    Strategy: remove all facts, plans, reviews, and agent executions for
    the run.  The workflow will be re-run from the intake stage.
    """
    db.query(ReviewResult).filter(ReviewResult.run_id == run_id).delete()
    db.query(PlanVersion).filter(PlanVersion.run_id == run_id).delete()
    db.query(AgentExecution).filter(AgentExecution.run_id == run_id).delete()
    db.query(Fact).filter(Fact.run_id == run_id).delete()
    db.query(HandoffRecord).filter(HandoffRecord.run_id == run_id).delete()
    run = get_run(db, run_id)
    if run:
        run.current_plan_version = None
        run.review_cycle_count = 0
        run.status = "CREATED"
        run.error_message = None
    db.commit()
