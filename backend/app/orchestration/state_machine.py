"""Workflow state machine — validates state transitions."""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# All valid workflow states
VALID_STATES = {
    "CREATED",
    "INTAKE_RUNNING",
    "INTAKE_COMPLETED",
    "PLANNING_RUNNING",
    "PLANNING_COMPLETED",
    "REVIEW_RUNNING",
    "NEEDS_CORRECTION",
    "APPROVED",
    "COMPLETED_WITH_UNRESOLVED_ISSUES",
    "FAILED",
    "INTERRUPTED",
}

# Allowed state transitions
TRANSITIONS: dict[str, set[str]] = {
    "CREATED": {"INTAKE_RUNNING"},
    "INTAKE_RUNNING": {"INTAKE_COMPLETED", "FAILED"},
    "INTAKE_COMPLETED": {"PLANNING_RUNNING"},
    "PLANNING_RUNNING": {"PLANNING_COMPLETED", "FAILED"},
    "PLANNING_COMPLETED": {"REVIEW_RUNNING"},
    "REVIEW_RUNNING": {"APPROVED", "NEEDS_CORRECTION",
                       "COMPLETED_WITH_UNRESOLVED_ISSUES", "FAILED"},
    "NEEDS_CORRECTION": {"PLANNING_RUNNING"},
    "APPROVED": set(),  # Terminal state
    "COMPLETED_WITH_UNRESOLVED_ISSUES": set(),  # Terminal state
    "FAILED": {"INTAKE_RUNNING", "PLANNING_RUNNING", "REVIEW_RUNNING",
               "CREATED"},  # Resume from failure
    "INTERRUPTED": {"INTAKE_RUNNING", "PLANNING_RUNNING", "REVIEW_RUNNING",
                    "CREATED"},  # Resume from interruption
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


def validate_transition(current_state: str, new_state: str) -> bool:
    """Check whether a state transition is valid."""
    if current_state not in VALID_STATES:
        raise InvalidTransitionError(f"Unknown current state: {current_state}")
    if new_state not in VALID_STATES:
        raise InvalidTransitionError(f"Unknown target state: {new_state}")

    allowed = TRANSITIONS.get(current_state, set())
    if new_state not in allowed:
        raise InvalidTransitionError(
            f"Invalid transition: {current_state} → {new_state}. "
            f"Allowed: {allowed}"
        )
    return True


def is_terminal(state: str) -> bool:
    """Check whether a state is terminal (no outgoing transitions)."""
    return state in {"APPROVED", "COMPLETED_WITH_UNRESOLVED_ISSUES"}


def is_failed(state: str) -> bool:
    """Check whether a state indicates failure."""
    return state in {"FAILED", "INTERRUPTED"}


def can_resume(state: str) -> bool:
    """Check whether a run in this state can be resumed."""
    return state in {"FAILED", "INTERRUPTED", "CREATED"}


def get_resume_target(failed_state: str, last_completed_stage: str | None) -> str:
    """Determine which state to resume from after failure.

    Returns the state the workflow should transition to on resume.
    """
    if last_completed_stage is None:
        return "INTAKE_RUNNING"
    elif last_completed_stage == "intake":
        return "PLANNING_RUNNING"
    elif last_completed_stage == "planning":
        return "REVIEW_RUNNING"
    else:
        return "INTAKE_RUNNING"
