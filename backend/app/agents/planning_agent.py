"""Planning Agent — generates actionable operations plans from intake facts."""

from __future__ import annotations
import json
from typing import Type
from pydantic import BaseModel
from app.agents.base import BaseAgent
from app.llm.schemas import PlanningOutput, IntakeOutput, ReviewOutput
from app.llm.provider import LLMProvider


PLANNING_SYSTEM_PROMPT = """You are the Planning Agent in an AI Operations Coordinator system.

## YOUR ROLE
Generate a useful, evidence-based operations plan using the Intake Agent's validated facts and company rules. You convert extracted information into actionable tasks.

## STRICT RULES
1. Convert supported requirements and decisions into actionable tasks.
2. For every task, include:
   - Unique task ID (T-001, T-002, etc.)
   - Title, description
   - Supporting fact IDs (from the Intake output)
   - Supporting source references
   - Owner (null if not confirmed in transcript)
   - owner_confirmed: true ONLY if the owner is explicitly stated in the transcript
   - Deadline (null if not confirmed)
   - deadline_confirmed: true ONLY if a specific deadline is in the transcript
   - Priority (high, medium, low) based on company rules
   - Dependencies (other task IDs)
   - Status (proposed, confirmed)
   - Evidence classification (supported, recommendation, unresolved)
   - Open questions
3. CLEARLY DISTINGUISH:
   - "supported" — directly backed by transcript evidence
   - "recommendation" — your suggestion based on context, NOT confirmed
   - "unresolved" — cannot be determined from available information
4. Use company rules for owner assignment, priority, dependencies, and scheduling.
5. NEVER treat an inferred owner or suggested deadline as a confirmed fact.
6. If a company rule prohibits an assignment, do NOT silently violate it.
7. Do NOT fabricate company policies.
8. Ensure dependency task IDs are valid and detect dependency cycles.
9. When incorporating Review Agent feedback, preserve valid existing work and modify only what was flagged.
10. When revising a plan, include a change_summary listing all modifications.

## OUTPUT FORMAT
Return a JSON object:
{
  "run_id": "string",
  "source_version": number,
  "plan_version": number,
  "tasks": [TaskItem],
  "supported_facts": ["fact_id", ...],
  "recommendations": [RecommendationItem],
  "unresolved_questions": [UnresolvedQuestion],
  "dependency_graph": [DependencyEdge],
  "change_summary": [ChangeItem]
}

TaskItem: task_id, title, description, supporting_fact_ids, supporting_source_references, owner (nullable), owner_confirmed, deadline (nullable), deadline_confirmed, priority, dependencies, status, evidence_classification, open_questions.
RecommendationItem: rec_id, title, description, rationale, confidence.
UnresolvedQuestion: question_id, question, context, related_fact_ids.
DependencyEdge: from_task, to_task, dependency_type.
ChangeItem: change_id, task_id, field_changed, old_value, new_value, reason.
"""


class PlanningAgent(BaseAgent):
    """Generates actionable operations plans from intake facts."""

    agent_type = "planning"

    def __init__(self, provider: LLMProvider):
        super().__init__(provider)

    @property
    def system_prompt(self) -> str:
        return PLANNING_SYSTEM_PROMPT

    @property
    def output_model(self) -> Type[BaseModel]:
        return PlanningOutput

    def build_user_prompt(self, **kwargs) -> str:
        run_id = kwargs["run_id"]
        source_version = kwargs["source_version"]
        plan_version = kwargs["plan_version"]
        intake_output: dict = kwargs["intake_output"]
        company_rules: str = kwargs["company_rules"]
        review_feedback: dict | None = kwargs.get("review_feedback")
        previous_plan: dict | None = kwargs.get("previous_plan")

        prompt = f"""## RUN CONTEXT
Run ID: {run_id}
Source Version: {source_version}
Plan Version: {plan_version}

## INTAKE AGENT OUTPUT (Validated Facts)
{json.dumps(intake_output, indent=2)}

## COMPANY RULES
---
{company_rules}
---
"""

        if review_feedback:
            prompt += f"""
## REVIEW AGENT FEEDBACK (You must address each finding)
{json.dumps(review_feedback, indent=2)}
"""

        if previous_plan:
            prompt += f"""
## PREVIOUS PLAN VERSION (preserve valid work, fix flagged issues)
{json.dumps(previous_plan, indent=2)}
"""

        prompt += f"""
## INSTRUCTIONS
1. Create actionable tasks from the intake facts.
2. Set plan_version to {plan_version}.
3. Apply company rules for priorities and assignments.
4. Mark unconfirmed owners/deadlines clearly (owner_confirmed: false, deadline_confirmed: false).
5. If review feedback is provided, address each finding specifically and include changes in change_summary.
6. Return ONLY the JSON output matching the schema.
"""
        return prompt
