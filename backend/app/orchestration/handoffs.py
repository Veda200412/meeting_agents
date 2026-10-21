"""Handoff validation between agents."""

from __future__ import annotations
import logging
from pydantic import ValidationError
from app.llm.schemas import IntakeOutput, PlanningOutput, ReviewOutput

logger = logging.getLogger(__name__)


class HandoffValidationError(Exception):
    """Raised when a handoff payload fails validation."""
    pass


def validate_intake_to_planning(intake_data: dict) -> IntakeOutput:
    """Validate the Intake Agent output before handing to Planning."""
    try:
        output = IntakeOutput.model_validate(intake_data)
    except ValidationError as e:
        raise HandoffValidationError(
            f"Intake→Planning handoff validation failed: {e}"
        ) from e

    # Check that at least some facts were extracted
    if not output.all_facts():
        logger.warning("Intake produced zero facts — Planning may have limited input")

    # Check that all facts have required evidence
    for fact in output.all_facts():
        if not fact.evidence_quote:
            raise HandoffValidationError(
                f"Fact {fact.fact_id} missing evidence_quote"
            )

    return output


def validate_planning_to_review(plan_data: dict) -> PlanningOutput:
    """Validate Planning Agent output before handing to Review."""
    try:
        output = PlanningOutput.model_validate(plan_data)
    except ValidationError as e:
        raise HandoffValidationError(
            f"Planning→Review handoff validation failed: {e}"
        ) from e

    # Check for dependency cycles
    _check_dependency_cycles(output)

    # Check that task IDs are unique
    task_ids = [t.task_id for t in output.tasks]
    if len(task_ids) != len(set(task_ids)):
        raise HandoffValidationError("Duplicate task IDs found in plan")

    # Check that dependency references are valid
    valid_ids = set(task_ids)
    for task in output.tasks:
        for dep in task.dependencies:
            if dep not in valid_ids:
                raise HandoffValidationError(
                    f"Task {task.task_id} depends on unknown task {dep}"
                )

    return output


def validate_review_output(review_data: dict) -> ReviewOutput:
    """Validate Review Agent output."""
    try:
        output = ReviewOutput.model_validate(review_data)
    except ValidationError as e:
        raise HandoffValidationError(
            f"Review output validation failed: {e}"
        ) from e

    if output.outcome not in ("APPROVED", "NEEDS_CORRECTION", "UNRESOLVED"):
        raise HandoffValidationError(
            f"Invalid review outcome: {output.outcome}"
        )

    return output


def _check_dependency_cycles(plan: PlanningOutput) -> None:
    """Detect cycles in the task dependency graph using DFS."""
    graph: dict[str, list[str]] = {}
    for task in plan.tasks:
        graph[task.task_id] = list(task.dependencies)
    for edge in plan.dependency_graph:
        if edge.from_task not in graph:
            graph[edge.from_task] = []
        graph[edge.from_task].append(edge.to_task)

    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        in_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor in in_stack:
                return True  # cycle found
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
        in_stack.discard(node)
        return False

    for node in graph:
        if node not in visited:
            if dfs(node):
                raise HandoffValidationError(
                    "Dependency cycle detected in the task graph"
                )
