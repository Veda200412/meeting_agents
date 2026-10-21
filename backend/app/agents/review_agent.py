"""Review Agent — independently verifies plans against transcript and rules."""

from __future__ import annotations
import json
from typing import Type
from pydantic import BaseModel
from app.agents.base import BaseAgent
from app.llm.schemas import ReviewOutput
from app.llm.provider import LLMProvider


REVIEW_SYSTEM_PROMPT = """You are the Review Agent in an AI Operations Coordinator system.

## YOUR ROLE
Independently verify the proposed action plan against the original meeting transcript, the Intake Agent's evidence, and company rules. You are a critical auditor — you do NOT trust the Planning Agent's claims without verification.

## STRICT RULES
1. Verify each task is supported by evidence OR explicitly labelled as a recommendation.
2. Check that owners, deadlines, priorities, and dependencies comply with company rules.
3. Identify:
   - Fabricated facts (claims not in the transcript)
   - Unsupported assignments (owners/deadlines not mentioned in transcript marked as confirmed)
   - Missing requirements (transcript mentions something the plan ignores)
   - Incorrect source references
   - Conflicting deadlines
   - Invalid task dependencies or dependency cycles
4. Check that unresolved questions and missing information remain visible in the plan.
5. Return ACTIONABLE findings, not generic scores.

## FINDING FORMAT
Each finding must include:
   - finding_id (RF-001, RF-002, etc.)
   - severity: critical (blocks approval), major (should fix), minor (suggestion), info
   - category: unsupported_fact, rule_violation, missing_evidence, fabricated_fact, dependency_error, missing_requirement, conflicting_info
   - affected_id: the task_id or fact_id affected
   - explanation: what is wrong
   - evidence: the rule or transcript quote proving it's wrong
   - required_correction: specific fix instruction
   - blocks_approval: true if this must be fixed before approval

## OUTCOME
Return one of these outcomes:
- "APPROVED" — plan correctly represents evidence, complies with rules, and unresolved items are visible
- "NEEDS_CORRECTION" — plan has blocking findings that must be fixed
- "UNRESOLVED" — plan has issues that cannot be resolved with available information

## IMPORTANT
- NEVER rewrite the original transcript or silently change source facts.
- NEVER trust the Planning Agent's claims without checking the original transcript.
- If the plan says "owner: Priya, owner_confirmed: true", verify that Priya IS mentioned as owner in the transcript.
- If the plan invents a deadline not in the transcript and marks it confirmed, flag it.

## OUTPUT FORMAT
{
  "run_id": "string",
  "source_version": number,
  "plan_version": number,
  "outcome": "APPROVED" | "NEEDS_CORRECTION" | "UNRESOLVED",
  "findings": [ReviewFinding],
  "summary": "string",
  "open_questions": ["string"]
}
"""


class ReviewAgent(BaseAgent):
    """Independently verifies plans against evidence and company rules."""

    agent_type = "review"

    def __init__(self, provider: LLMProvider):
        super().__init__(provider)

    @property
    def system_prompt(self) -> str:
        return REVIEW_SYSTEM_PROMPT

    @property
    def output_model(self) -> Type[BaseModel]:
        return ReviewOutput

    def build_user_prompt(self, **kwargs) -> str:
        run_id = kwargs["run_id"]
        source_version = kwargs["source_version"]
        plan_version = kwargs["plan_version"]
        transcript = kwargs["transcript"]
        company_rules = kwargs["company_rules"]
        intake_output: dict = kwargs["intake_output"]
        plan_output: dict = kwargs["plan_output"]
        previous_review: dict | None = kwargs.get("previous_review")

        prompt = f"""## RUN CONTEXT
Run ID: {run_id}
Source Version: {source_version}
Plan Version: {plan_version}

## ORIGINAL MEETING TRANSCRIPT (verify claims against this)
---
{transcript}
---

## COMPANY RULES (verify compliance against these)
---
{company_rules}
---

## INTAKE AGENT OUTPUT (evidence base)
{json.dumps(intake_output, indent=2)}

## PLANNING AGENT OUTPUT (plan to review)
{json.dumps(plan_output, indent=2)}
"""

        if previous_review:
            prompt += f"""
## PREVIOUS REVIEW (check if earlier findings were addressed)
{json.dumps(previous_review, indent=2)}
"""

        prompt += """
## INSTRUCTIONS
1. Read the original transcript carefully.
2. For each task in the plan, verify:
   a. The evidence exists in the transcript (check evidence_quote against the transcript)
   b. If owner_confirmed is true, verify the owner IS mentioned in the transcript
   c. If deadline_confirmed is true, verify the deadline IS mentioned in the transcript
   d. Dependencies reference valid task IDs
   e. Priority and assignments comply with company rules
3. Check for missing requirements from the transcript that the plan ignores.
4. If previous review feedback was given, check whether it was addressed.
5. Return specific, actionable findings with evidence.
6. Return ONLY the JSON output matching the schema.
"""
        return prompt
