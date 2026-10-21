"""FastAPI routes — all API endpoints for the Operations Coordinator."""

from __future__ import annotations
import os
import uuid
import threading
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.core.security import sanitize_text, MAX_TRANSCRIPT_LENGTH, MAX_RULES_LENGTH
from app.db.database import get_db, get_session_factory
from app.db import repository as repo
from app.llm.schemas import (
    CreateRunRequest, CorrectionRequest, RunSummary,
    HealthResponse,
)
from app.orchestration.workflow import execute_workflow, resume_workflow, WorkflowError
from app.orchestration.state_machine import can_resume

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _get_owned_run(db: Session, run_id: str, user_id: str):
    """Return a run only when it belongs to the authenticated user."""
    run = repo.get_run(db, run_id)
    if not run or run.owner_id != user_id:
        raise HTTPException(404, "Run not found")
    return run


# ── Sample Data ───────────────────────────────────────

SAMPLE_TRANSCRIPTS = {
    "simple": (
        "During the operations meeting, the team agreed to prepare the customer "
        "onboarding checklist before the next review meeting. Priya will draft "
        "the checklist. The engineering team must confirm the API dependencies "
        "before implementation starts. No exact deadline was agreed for the API "
        "dependency review."
    ),
    "complex": (
        "The Q3 planning meeting covered multiple topics. Sarah mentioned that "
        "the migration to the new payment provider must be completed by end of "
        "October. However, David disagreed and said the legal review hasn't "
        "finished yet, so October is not realistic. The team discussed the "
        "customer feedback dashboard — Alex volunteered to lead the frontend "
        "work, but no backend owner was identified. Maria raised a risk about "
        "the data pipeline reliability: 'We had three outages last month and "
        "the root cause analysis is still pending.' The security audit was "
        "mentioned as a dependency for the payment migration, but nobody "
        "confirmed who would schedule it. Budget allocation for the new hire "
        "was approved, but the job description hasn't been written yet. "
        "Tom suggested deploying to staging by next Friday, while Sarah said "
        "the staging environment won't be ready until the following Monday. "
        "There was no resolution on this conflict."
    ),
}

SAMPLE_RULES = {
    "simple": (
        "Company Operations Rules:\n"
        "1. Only explicitly confirmed owners from the meeting transcript may be "
        "treated as confirmed task owners.\n"
        "2. Do not invent exact deadlines that were not agreed upon in the meeting.\n"
        "3. All tasks must respect their stated dependencies before starting.\n"
        "4. Recommendations must be clearly labelled separately from confirmed facts.\n"
        "5. If a task has no confirmed owner, it must be flagged for assignment.\n"
        "6. Priority should be based on dependency criticality and explicit urgency."
    ),
    "complex": (
        "Company Operations Rules:\n"
        "1. Only explicitly confirmed owners may be treated as confirmed.\n"
        "2. Do not invent deadlines not agreed upon in the meeting.\n"
        "3. Tasks must respect dependencies.\n"
        "4. Recommendations must be labelled separately from facts.\n"
        "5. Security audits must be completed before any payment-related changes.\n"
        "6. Legal review completion is a prerequisite for external vendor changes.\n"
        "7. All conflicting statements must be preserved and flagged for resolution.\n"
        "8. Budget approvals require documented job descriptions before hiring begins.\n"
        "9. Staging deployments require environment readiness confirmation.\n"
        "10. Risk items with pending root cause analysis must be treated as blockers."
    ),
}


def _run_workflow_background(run_id: str):
    """Execute workflow in a background thread with its own DB session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        execute_workflow(run_id, db)
    finally:
        db.close()


def _resume_workflow_background(run_id: str):
    """Resume workflow in a background thread with its own DB session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        resume_workflow(run_id, db)
    finally:
        db.close()


def _launch_workflow(run_id: str, db: Session, resume: bool = False) -> None:
    """Run inline on Vercel; use a background worker for persistent local servers."""
    if os.environ.get("VERCEL") == "1":
        if resume:
            resume_workflow(run_id, db)
        else:
            execute_workflow(run_id, db)
        return

    target = _resume_workflow_background if resume else _run_workflow_background
    threading.Thread(target=target, args=(run_id,), daemon=True).start()


# ── Health ────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        llm_configured=bool(settings.GOOGLE_API_KEY),
        demo_faults_enabled=settings.ENABLE_DEMO_FAULTS,
    )


# ── Sample Data ───────────────────────────────────────

@router.get("/samples")
def get_samples():
    """Return available sample transcripts and rules."""
    return {
        "transcripts": {k: v for k, v in SAMPLE_TRANSCRIPTS.items()},
        "rules": {k: v for k, v in SAMPLE_RULES.items()},
    }


# ── Runs ──────────────────────────────────────────────

@router.post("/runs")
def create_run(
    request: CreateRunRequest,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Create a new workflow run."""
    settings = get_settings()

    transcript = sanitize_text(request.transcript, MAX_TRANSCRIPT_LENGTH)
    rules = sanitize_text(request.company_rules, MAX_RULES_LENGTH)
    run_id = str(uuid.uuid4())

    fault = None
    if request.fault_injection and settings.ENABLE_DEMO_FAULTS:
        if request.fault_injection in ("intake_failure", "schema_failure", "planning_failure"):
            fault = request.fault_injection
        else:
            raise HTTPException(400, f"Unknown fault type: {request.fault_injection}")

    run_name = request.title or request.name or "Operations Coordination"
    run = repo.create_run(
        db, run_id, run_name, transcript, rules,
        max_review_cycles=settings.MAX_REVIEW_CYCLES,
        owner_id=user["id"],
    )

    if fault:
        repo.set_run_fault(db, run_id, fault)

    # Vercel serverless workers cannot guarantee background-thread completion.
    if not os.environ.get("TESTING"):
        _launch_workflow(run_id, db)

    return {
        "id": run.id,
        "name": run.name,
        "title": run.name,
        "status": run.status,
        "created_at": run.created_at.isoformat(),
    }


@router.get("/runs")
def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """List all runs with pagination."""
    runs = repo.list_runs(db, user["id"], limit, offset)
    return [
        {
            "id": r.id,
            "name": r.name,
            "title": r.name,
            "status": r.status,
            "current_source_version": r.current_source_version,
            "current_plan_version": r.current_plan_version,
            "review_cycle_count": r.review_cycle_count,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
            "error_message": r.error_message,
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Get full run detail."""
    run = _get_owned_run(db, run_id, user["id"])

    source = repo.get_source_version(db, run_id, run.current_source_version)
    facts = repo.get_facts(db, run_id, run.current_source_version)
    current_plan = repo.get_current_plan(db, run_id)
    all_plans = repo.get_all_plans(db, run_id)
    all_reviews = repo.get_all_reviews(db, run_id)
    executions = repo.get_executions(db, run_id)
    handoffs = repo.get_handoffs(db, run_id)
    corrections = repo.get_corrections(db, run_id)

    latest_review = None
    if current_plan:
        latest_review = repo.get_review_for_plan(db, run_id, current_plan.version)

    return {
        "id": run.id,
        "name": run.name,
        "title": run.name,
        "status": run.status,
        "current_source_version": run.current_source_version,
        "current_plan_version": run.current_plan_version,
        "review_cycle_count": run.review_cycle_count,
        "max_review_cycles": run.max_review_cycles,
        "fault_injection": run.fault_injection,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
        "source": {
            "version": source.version,
            "transcript": source.transcript,
            "company_rules": source.company_rules,
        } if source else None,
        "facts": [
            {
                "fact_id": f.fact_id, "fact_type": f.fact_type,
                "content": f.content, "evidence_quote": f.evidence_quote,
                "source_location": f.source_location,
                "confidence": f.confidence, "owner": f.owner,
                "deadline": f.deadline,
                "missing_fields": f.missing_fields or [],
                "notes": f.notes,
            }
            for f in facts
        ],
        "current_plan": {
            "version": current_plan.version,
            "source_version": current_plan.source_version,
            "tasks": current_plan.tasks,
            "supported_facts": current_plan.supported_facts,
            "recommendations": current_plan.recommendations,
            "unresolved_questions": current_plan.unresolved_questions,
            "dependency_graph": current_plan.dependency_graph,
            "change_summary": current_plan.change_summary,
            "created_at": current_plan.created_at.isoformat(),
        } if current_plan else None,
        "all_plans": [
            {
                "version": p.version,
                "source_version": p.source_version,
                "tasks": p.tasks,
                "supported_facts": p.supported_facts,
                "recommendations": p.recommendations,
                "unresolved_questions": p.unresolved_questions,
                "dependency_graph": p.dependency_graph,
                "change_summary": p.change_summary,
                "created_at": p.created_at.isoformat(),
            }
            for p in all_plans
        ],
        "latest_review": {
            "plan_version": latest_review.plan_version,
            "source_version": latest_review.source_version,
            "outcome": latest_review.outcome,
            "findings": latest_review.findings,
            "summary": latest_review.summary,
            "open_questions": latest_review.open_questions,
            "created_at": latest_review.created_at.isoformat(),
        } if latest_review else None,
        "all_reviews": [
            {
                "plan_version": r.plan_version,
                "source_version": r.source_version,
                "outcome": r.outcome,
                "findings": r.findings,
                "summary": r.summary,
                "open_questions": r.open_questions,
                "created_at": r.created_at.isoformat(),
            }
            for r in all_reviews
        ],
        "executions": [
            {
                "id": e.id,
                "agent_type": e.agent_type,
                "step_id": e.step_id,
                "attempt_number": e.attempt_number,
                "status": e.status,
                "started_at": e.started_at.isoformat(),
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "error_message": e.error_message,
                "source_version": e.source_version,
                "plan_version": e.plan_version,
            }
            for e in executions
        ],
        "handoffs": [
            {
                "from_agent": h.from_agent,
                "to_agent": h.to_agent,
                "summary": h.payload_summary,
                "payload": h.payload,
                "source_version": h.source_version,
                "plan_version": h.plan_version,
                "created_at": h.created_at.isoformat(),
            }
            for h in handoffs
        ],
        "corrections": [
            {
                "id": c.id, "fact_id": c.fact_id,
                "field_name": c.field_name,
                "original_value": c.original_value,
                "corrected_value": c.corrected_value,
                "correction_note": c.correction_note,
                "new_source_version": c.new_source_version,
                "created_at": c.created_at.isoformat(),
            }
            for c in corrections
        ],
    }


@router.post("/runs/{run_id}/start")
def start_workflow(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Start or resume workflow execution."""
    run = _get_owned_run(db, run_id, user["id"])

    if run.status not in ("CREATED",):
        raise HTTPException(
            400,
            f"Cannot start run in state {run.status}. "
            "Use /resume for failed runs."
        )

    _launch_workflow(run_id, db)

    return {"message": "Workflow started", "run_id": run_id}


@router.get("/runs/{run_id}/events")
def get_events(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Get workflow events for the timeline."""
    _get_owned_run(db, run_id, user["id"])

    events = repo.get_events(db, run_id)
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "agent_type": e.agent_type,
            "description": e.description,
            "version_info": e.version_info,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/runs/{run_id}/agents")
def get_agent_executions(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Get agent execution details."""
    _get_owned_run(db, run_id, user["id"])

    execs = repo.get_executions(db, run_id)
    return [
        {
            "id": e.id,
            "agent_type": e.agent_type,
            "step_id": e.step_id,
            "attempt_number": e.attempt_number,
            "status": e.status,
            "started_at": e.started_at.isoformat(),
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "input_snapshot": e.input_snapshot,
            "output_snapshot": e.output_snapshot,
            "error_message": e.error_message,
            "source_version": e.source_version,
            "plan_version": e.plan_version,
        }
        for e in execs
    ]


@router.get("/runs/{run_id}/plans")
def get_plan_versions(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Get all plan versions with review results."""
    _get_owned_run(db, run_id, user["id"])

    plans = repo.get_all_plans(db, run_id)
    reviews = repo.get_all_reviews(db, run_id)
    review_map = {r.plan_version: r for r in reviews}

    return [
        {
            "version": p.version,
            "source_version": p.source_version,
            "tasks": p.tasks,
            "supported_facts": p.supported_facts,
            "recommendations": p.recommendations,
            "unresolved_questions": p.unresolved_questions,
            "dependency_graph": p.dependency_graph,
            "change_summary": p.change_summary,
            "created_at": p.created_at.isoformat(),
            "review": {
                "outcome": review_map[p.version].outcome,
                "findings": review_map[p.version].findings,
                "summary": review_map[p.version].summary,
                "open_questions": review_map[p.version].open_questions,
            } if p.version in review_map else None,
        }
        for p in plans
    ]


@router.get("/runs/{run_id}/plan")
def get_current_plan(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Get the current plan and its evidence."""
    _get_owned_run(db, run_id, user["id"])

    plan = repo.get_current_plan(db, run_id)
    if not plan:
        return {"plan": None, "review": None}

    review = repo.get_review_for_plan(db, run_id, plan.version)

    return {
        "plan": {
            "version": plan.version,
            "source_version": plan.source_version,
            "tasks": plan.tasks,
            "supported_facts": plan.supported_facts,
            "recommendations": plan.recommendations,
            "unresolved_questions": plan.unresolved_questions,
            "dependency_graph": plan.dependency_graph,
            "change_summary": plan.change_summary,
        },
        "review": {
            "outcome": review.outcome,
            "findings": review.findings,
            "summary": review.summary,
            "open_questions": review.open_questions,
        } if review else None,
    }


@router.post("/runs/{run_id}/corrections")
def submit_correction(
    run_id: str, request: CorrectionRequest,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Submit a fact correction and invalidate affected stages."""
    run = _get_owned_run(db, run_id, user["id"])

    # Find the fact
    facts = repo.get_facts(db, run_id, run.current_source_version)
    target_fact = None
    for f in facts:
        if f.fact_id == request.fact_id:
            target_fact = f
            break

    if not target_fact:
        raise HTTPException(404, f"Fact {request.fact_id} not found")

    original_value = getattr(target_fact, request.field_name, None)
    new_source_version = run.current_source_version + 1

    # Save correction record
    repo.save_correction(
        db, run_id, request.fact_id, request.field_name,
        str(original_value) if original_value is not None else None,
        request.corrected_value, request.correction_note,
        new_source_version,
    )

    # Create new source version with same transcript/rules
    current_source = repo.get_current_source(db, run_id)
    if current_source:
        repo.create_source_version(
            db, run_id, new_source_version,
            current_source.transcript, current_source.company_rules,
        )

    # Invalidate downstream
    repo.invalidate_downstream(db, run_id)

    repo.add_event(db, run_id, "fact_corrected", None,
                   f"Fact {request.fact_id}.{request.field_name} corrected. "
                   f"Source version: {new_source_version}",
                   {"fact_id": request.fact_id, "field": request.field_name,
                    "new_source_version": new_source_version})
    db.commit()

    # Automatically trigger workflow execution with the new source version
    if not os.environ.get("TESTING"):
        _launch_workflow(run_id, db)

    return {
        "message": "Correction applied, workflow restarted",
        "new_source_version": new_source_version,
        "status": "INTAKE_RUNNING",
    }


@router.get("/runs/{run_id}/handoffs")
def get_handoffs(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Get formal handoff records for a run."""
    _get_owned_run(db, run_id, user["id"])

    handoffs = repo.get_handoffs(db, run_id)
    return [
        {
            "from_agent": h.from_agent,
            "to_agent": h.to_agent,
            "summary": h.payload_summary,
            "payload": h.payload,
            "source_version": h.source_version,
            "plan_version": h.plan_version,
            "created_at": h.created_at.isoformat(),
        }
        for h in handoffs
    ]


@router.post("/runs/{run_id}/resume")
def resume_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Resume a failed or interrupted run."""
    run = _get_owned_run(db, run_id, user["id"])

    if not can_resume(run.status):
        raise HTTPException(
            400,
            f"Cannot resume run in state {run.status}. "
            "Only FAILED or INTERRUPTED runs can be resumed."
        )

    _launch_workflow(run_id, db, resume=True)

    return {"message": "Workflow resumed", "run_id": run_id}


@router.post("/runs/{run_id}/reset")
def reset_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, str] = Depends(get_current_user),
):
    """Reset (delete) a run with all its data."""
    _get_owned_run(db, run_id, user["id"])

    deleted = repo.delete_run(db, run_id)
    if not deleted:
        raise HTTPException(500, "Failed to delete run")

    return {"message": "Run deleted", "run_id": run_id}
