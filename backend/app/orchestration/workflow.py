"""Workflow orchestrator — runs the three-agent pipeline with review-correction loop."""

from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import safe_error_message
from app.llm.provider import LLMProvider, LLMProviderError, LLMSchemaError, create_provider
from app.llm.schemas import IntakeOutput, PlanningOutput, ReviewOutput
from app.agents.intake_agent import IntakeAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.review_agent import ReviewAgent
from app.orchestration.state_machine import validate_transition, can_resume, get_resume_target
from app.orchestration.handoffs import (
    validate_intake_to_planning,
    validate_planning_to_review,
    validate_review_output,
    HandoffValidationError,
)
from app.db import repository as repo

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Non-retryable workflow error."""
    pass


class DemoFaultError(Exception):
    """Simulated fault for demo purposes."""
    pass


def _step_id(run_id: str, agent: str, source_version: int, plan_version: int = 0) -> str:
    """Generate a deterministic step ID for idempotency."""
    return f"{run_id}:{agent}:sv{source_version}:pv{plan_version}"


def execute_workflow(run_id: str, db: Session,
                     provider: LLMProvider | None = None) -> None:
    """Execute the full three-agent workflow for a run.

    This function is designed to be called in a background thread.
    It persists all state to the database at each step.
    """
    settings = get_settings()

    try:
        if provider is None:
            provider = create_provider()
    except LLMProviderError as e:
        repo.update_run_status(db, run_id, "FAILED", safe_error_message(e))
        repo.add_event(db, run_id, "workflow_failed", None,
                       f"LLM provider initialization failed: {safe_error_message(e)}")
        db.commit()
        return

    run = repo.get_run(db, run_id)
    if not run:
        logger.error("Run %s not found", run_id)
        return

    source_version = run.current_source_version
    source = repo.get_source_version(db, run_id, source_version)
    if not source:
        repo.update_run_status(db, run_id, "FAILED", "Source version not found")
        return

    max_cycles = run.max_review_cycles

    try:
        # ── STEP 1: Intake Agent ──────────────────────────────
        intake_output = _run_intake(
            run_id, source_version, source.transcript, source.company_rules,
            db, provider, run.fault_injection
        )

        # ── STEP 2: Planning Agent (initial) ──────────────────
        plan_version = 1
        plan_output = _run_planning(
            run_id, source_version, plan_version,
            intake_output, source.company_rules,
            db, provider, run.fault_injection
        )

        # ── STEP 3: Review-correction loop ────────────────────
        review_feedback = None
        for cycle in range(max_cycles + 1):
            review_output = _run_review(
                run_id, source_version, plan_version,
                source.transcript, source.company_rules,
                intake_output, plan_output,
                review_feedback,
                db, provider
            )

            if review_output.outcome == "APPROVED":
                _transition(db, run_id, "APPROVED")
                repo.add_event(db, run_id, "workflow_approved", "review",
                               f"Plan v{plan_version} approved",
                               {"plan_version": plan_version, "source_version": source_version})
                db.commit()
                logger.info("Run %s approved at plan version %d", run_id, plan_version)
                return

            if review_output.outcome == "NEEDS_CORRECTION" and cycle < max_cycles:
                repo.save_handoff(
                    db, run_id, "review", "planning",
                    f"Returned {len(review_output.findings)} finding(s) for plan v{plan_version}",
                    source_version, plan_version,
                    payload=review_output.model_dump(),
                )
                _transition(db, run_id, "NEEDS_CORRECTION")
                repo.add_event(db, run_id, "correction_needed", "review",
                               f"Plan v{plan_version} needs correction (cycle {cycle + 1}/{max_cycles})",
                               {"plan_version": plan_version, "cycle": cycle + 1})
                db.commit()

                review_feedback = review_output.model_dump()
                plan_version += 1
                run.review_cycle_count = cycle + 1
                db.commit()

                plan_output = _run_planning(
                    run_id, source_version, plan_version,
                    intake_output, source.company_rules,
                    db, provider, fault_injection=None,
                    review_feedback=review_feedback,
                    previous_plan=plan_output,
                )
            else:
                # Max cycles reached or UNRESOLVED
                _transition(db, run_id, "COMPLETED_WITH_UNRESOLVED_ISSUES")
                repo.add_event(db, run_id, "workflow_unresolved", "review",
                               f"Workflow completed with unresolved issues after {cycle + 1} review(s)",
                               {"plan_version": plan_version, "cycles": cycle + 1})
                db.commit()
                logger.info("Run %s completed with unresolved issues", run_id)
                return

    except DemoFaultError as e:
        repo.update_run_status(db, run_id, "FAILED", f"[SIMULATED] {str(e)}")
        repo.add_event(db, run_id, "simulated_failure", None,
                       f"Simulated failure: {str(e)}")
        db.commit()

    except (LLMProviderError, LLMSchemaError) as e:
        repo.update_run_status(db, run_id, "FAILED", safe_error_message(e))
        repo.add_event(db, run_id, "llm_error", None,
                       f"LLM error: {safe_error_message(e)}")
        db.commit()

    except HandoffValidationError as e:
        repo.update_run_status(db, run_id, "FAILED", str(e)[:500])
        repo.add_event(db, run_id, "handoff_error", None,
                       f"Handoff validation error: {str(e)[:300]}")
        db.commit()

    except Exception as e:
        logger.exception("Unexpected error in workflow %s", run_id)
        repo.update_run_status(db, run_id, "FAILED", safe_error_message(e))
        repo.add_event(db, run_id, "workflow_error", None,
                       f"Unexpected error: {safe_error_message(e)}")
        db.commit()


def resume_workflow(run_id: str, db: Session,
                    provider: LLMProvider | None = None) -> None:
    """Resume a failed or interrupted workflow from the earliest incomplete step."""
    run = repo.get_run(db, run_id)
    if not run:
        raise WorkflowError(f"Run {run_id} not found")

    if not can_resume(run.status):
        raise WorkflowError(
            f"Cannot resume run in state {run.status}. "
            "Only FAILED or INTERRUPTED runs can be resumed."
        )

    # Clear fault injection on resume
    if run.fault_injection:
        run.fault_injection = None
        db.commit()

    repo.add_event(db, run_id, "workflow_resumed", None,
                   f"Resuming from state {run.status}")
    db.commit()

    # Reset status to CREATED so the workflow can restart
    run.status = "CREATED"
    run.error_message = None
    db.commit()

    execute_workflow(run_id, db, provider)


# ── Private helpers ───────────────────────────────────

def _transition(db: Session, run_id: str, new_status: str) -> None:
    """Transition run to a new state with validation."""
    run = repo.get_run(db, run_id)
    if not run:
        raise WorkflowError(f"Run {run_id} not found")
    validate_transition(run.status, new_status)
    repo.update_run_status(db, run_id, new_status)


def _run_intake(
    run_id: str, source_version: int,
    transcript: str, company_rules: str,
    db: Session, provider: LLMProvider,
    fault_injection: str | None,
) -> dict:
    """Execute the Intake Agent stage."""
    step_id = _step_id(run_id, "intake", source_version)

    # Idempotency: reuse completed step
    existing = repo.get_completed_step(db, step_id)
    if existing and existing.output_snapshot:
        logger.info("Reusing completed intake step %s", step_id)
        repo.add_event(db, run_id, "step_reused", "intake",
                       "Reusing previously completed intake step",
                       {"source_version": source_version})
        db.commit()
        # Still need to transition through the states
        run = repo.get_run(db, run_id)
        if run.status == "CREATED":
            _transition(db, run_id, "INTAKE_RUNNING")
            _transition(db, run_id, "INTAKE_COMPLETED")
        return existing.output_snapshot

    # Check for demo fault
    if fault_injection == "intake_failure":
        _transition(db, run_id, "INTAKE_RUNNING")
        repo.create_execution(db, run_id, "intake", step_id, source_version,
                              input_snapshot={"transcript_length": len(transcript)})
        repo.complete_execution(db, step_id, error="[SIMULATED] Model failure during intake")
        repo.add_event(db, run_id, "agent_failed", "intake",
                       "[SIMULATED] Intake agent model failure")
        db.commit()
        raise DemoFaultError("Model failure during Intake Agent execution")

    if fault_injection == "schema_failure":
        _transition(db, run_id, "INTAKE_RUNNING")
        repo.create_execution(db, run_id, "intake", step_id, source_version,
                              input_snapshot={"transcript_length": len(transcript)})
        repo.complete_execution(db, step_id, error="[SIMULATED] Schema validation failure")
        repo.add_event(db, run_id, "agent_failed", "intake",
                       "[SIMULATED] Schema validation failure in intake")
        db.commit()
        raise DemoFaultError("Schema validation failure during Intake Agent")

    _transition(db, run_id, "INTAKE_RUNNING")
    repo.add_event(db, run_id, "agent_started", "intake",
                   "Intake Agent started extracting facts",
                   {"source_version": source_version})
    db.commit()

    # Get user corrections if any
    corrections = repo.get_corrections(db, run_id)
    correction_list = [
        {
            "fact_id": c.fact_id, "field_name": c.field_name,
            "corrected_value": c.corrected_value,
            "correction_note": c.correction_note,
        }
        for c in corrections
    ]

    execution = repo.create_execution(
        db, run_id, "intake", step_id, source_version,
        input_snapshot={"transcript_length": len(transcript),
                        "rules_length": len(company_rules),
                        "corrections": len(correction_list)},
    )

    agent = IntakeAgent(provider)
    result = agent.execute(
        run_id=run_id, source_version=source_version,
        transcript=transcript, company_rules=company_rules,
        user_corrections=correction_list,
    )

    # Validate
    intake_data = result.model_dump()
    intake_data["run_id"] = run_id
    intake_data["source_version"] = source_version
    validated = validate_intake_to_planning(intake_data)

    # Persist facts
    for fact in validated.all_facts():
        repo.save_facts(db, run_id, source_version, [fact.model_dump()])

    repo.complete_execution(db, step_id, output_snapshot=intake_data)
    repo.save_handoff(db, run_id, "intake", "planning",
                      f"Extracted {len(validated.all_facts())} facts",
                      source_version, payload=intake_data)
    repo.add_event(db, run_id, "agent_completed", "intake",
                   f"Intake Agent extracted {len(validated.all_facts())} facts",
                   {"source_version": source_version,
                    "fact_count": len(validated.all_facts())})
    _transition(db, run_id, "INTAKE_COMPLETED")
    db.commit()

    return intake_data


def _run_planning(
    run_id: str, source_version: int, plan_version: int,
    intake_output: dict, company_rules: str,
    db: Session, provider: LLMProvider,
    fault_injection: str | None = None,
    review_feedback: dict | None = None,
    previous_plan: dict | None = None,
) -> dict:
    """Execute the Planning Agent stage."""
    step_id = _step_id(run_id, "planning", source_version, plan_version)

    # Idempotency
    existing = repo.get_completed_step(db, step_id)
    if existing and existing.output_snapshot:
        logger.info("Reusing completed planning step %s", step_id)
        repo.add_event(db, run_id, "step_reused", "planning",
                       f"Reusing previously completed planning step (plan v{plan_version})")
        db.commit()
        run = repo.get_run(db, run_id)
        if run.status in ("INTAKE_COMPLETED", "NEEDS_CORRECTION"):
            _transition(db, run_id, "PLANNING_RUNNING")
            _transition(db, run_id, "PLANNING_COMPLETED")
        return existing.output_snapshot

    if fault_injection == "planning_failure":
        run = repo.get_run(db, run_id)
        if run.status in ("INTAKE_COMPLETED", "NEEDS_CORRECTION"):
            _transition(db, run_id, "PLANNING_RUNNING")
        repo.create_execution(db, run_id, "planning", step_id, source_version,
                              plan_version=plan_version)
        repo.complete_execution(db, step_id, error="[SIMULATED] Planning agent failure")
        repo.add_event(db, run_id, "agent_failed", "planning",
                       "[SIMULATED] Planning agent failure")
        db.commit()
        raise DemoFaultError("Model failure during Planning Agent execution")

    _transition(db, run_id, "PLANNING_RUNNING")
    repo.add_event(db, run_id, "agent_started", "planning",
                   f"Planning Agent started (plan v{plan_version})",
                   {"source_version": source_version, "plan_version": plan_version})
    db.commit()

    execution = repo.create_execution(
        db, run_id, "planning", step_id, source_version,
        plan_version=plan_version,
        input_snapshot={"has_feedback": review_feedback is not None,
                        "plan_version": plan_version},
    )

    agent = PlanningAgent(provider)
    result = agent.execute(
        run_id=run_id, source_version=source_version,
        plan_version=plan_version, intake_output=intake_output,
        company_rules=company_rules,
        review_feedback=review_feedback,
        previous_plan=previous_plan,
    )

    plan_data = result.model_dump()
    plan_data["run_id"] = run_id
    plan_data["source_version"] = source_version
    plan_data["plan_version"] = plan_version
    validated = validate_planning_to_review(plan_data)

    repo.save_plan_version(db, run_id, plan_version, source_version, plan_data)
    repo.complete_execution(db, step_id, output_snapshot=plan_data)
    repo.save_handoff(db, run_id, "planning", "review",
                      f"Generated plan v{plan_version} with {len(validated.tasks)} tasks",
                      source_version, plan_version, payload=plan_data)
    repo.add_event(db, run_id, "agent_completed", "planning",
                   f"Planning Agent created plan v{plan_version} with {len(validated.tasks)} tasks",
                   {"plan_version": plan_version, "task_count": len(validated.tasks)})
    _transition(db, run_id, "PLANNING_COMPLETED")
    db.commit()

    return plan_data


def _run_review(
    run_id: str, source_version: int, plan_version: int,
    transcript: str, company_rules: str,
    intake_output: dict, plan_output: dict,
    previous_review: dict | None,
    db: Session, provider: LLMProvider,
) -> ReviewOutput:
    """Execute the Review Agent stage."""
    step_id = _step_id(run_id, "review", source_version, plan_version)

    existing = repo.get_completed_step(db, step_id)
    if existing and existing.output_snapshot:
        logger.info("Reusing completed review step %s", step_id)
        run = repo.get_run(db, run_id)
        if run.status == "PLANNING_COMPLETED":
            _transition(db, run_id, "REVIEW_RUNNING")
        validated = validate_review_output(existing.output_snapshot)
        # Still need to transition to proper state
        if validated.outcome == "APPROVED":
            pass  # caller handles
        elif validated.outcome == "NEEDS_CORRECTION":
            pass
        else:
            pass
        return validated

    _transition(db, run_id, "REVIEW_RUNNING")
    repo.add_event(db, run_id, "agent_started", "review",
                   f"Review Agent started reviewing plan v{plan_version}",
                   {"plan_version": plan_version, "source_version": source_version})
    db.commit()

    execution = repo.create_execution(
        db, run_id, "review", step_id, source_version,
        plan_version=plan_version,
        input_snapshot={"plan_version": plan_version,
                        "has_previous_review": previous_review is not None},
    )

    agent = ReviewAgent(provider)
    result = agent.execute(
        run_id=run_id, source_version=source_version,
        plan_version=plan_version, transcript=transcript,
        company_rules=company_rules,
        intake_output=intake_output, plan_output=plan_output,
        previous_review=previous_review,
    )

    review_data = result.model_dump()
    review_data["run_id"] = run_id
    review_data["source_version"] = source_version
    review_data["plan_version"] = plan_version
    validated = validate_review_output(review_data)

    repo.save_review_result(
        db, run_id, plan_version, source_version,
        validated.outcome, [f.model_dump() for f in validated.findings],
        validated.summary, validated.open_questions,
    )
    repo.complete_execution(db, step_id, output_snapshot=review_data)
    repo.add_event(db, run_id, "agent_completed", "review",
                   f"Review Agent: {validated.outcome} "
                   f"({len(validated.findings)} findings)",
                   {"plan_version": plan_version,
                    "outcome": validated.outcome,
                    "findings_count": len(validated.findings)})
    db.commit()

    return validated
