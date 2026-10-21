"""Pydantic schemas for all agent inputs and outputs."""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════
#  INTAKE AGENT SCHEMAS
# ═══════════════════════════════════════════════════════

class SourceReference(BaseModel):
    """A reference into the original transcript."""
    ref_id: str = Field(..., description="Unique reference ID, e.g. SR-001")
    quote: str = Field(..., description="Exact or concise verbatim excerpt")
    location: str = Field(..., description="Character offsets or line numbers")
    context: str = Field(default="", description="Surrounding context")


class FactItem(BaseModel):
    """A single extracted fact with evidence."""
    fact_id: str = Field(..., description="Unique fact ID, e.g. F-001")
    fact_type: str = Field(
        ..., description="Type: decision, requirement, constraint, action_item, risk, conflict, missing_info"
    )
    content: str = Field(..., description="Description of the fact")
    evidence_quote: str = Field(..., description="Exact source quote supporting this fact")
    source_location: str = Field(..., description="Location in the transcript")
    confidence: str = Field(
        ..., description="One of: explicit, interpretation, missing, conflicting"
    )
    owner: Optional[str] = Field(default=None, description="Person responsible, null if not specified")
    deadline: Optional[str] = Field(default=None, description="Deadline if mentioned, null if not specified")
    missing_fields: list[str] = Field(default_factory=list, description="Fields not found in transcript")
    notes: str = Field(default="", description="Additional notes or explanation")


class IntakeOutput(BaseModel):
    """Validated output from the Intake Agent."""
    run_id: str
    source_version: int
    decisions: list[FactItem] = Field(default_factory=list)
    requirements: list[FactItem] = Field(default_factory=list)
    constraints: list[FactItem] = Field(default_factory=list)
    action_items: list[FactItem] = Field(default_factory=list)
    risks: list[FactItem] = Field(default_factory=list)
    conflicts: list[FactItem] = Field(default_factory=list)
    missing_information: list[FactItem] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)

    def all_facts(self) -> list[FactItem]:
        """Return all facts across all categories."""
        return (
            self.decisions + self.requirements + self.constraints +
            self.action_items + self.risks + self.conflicts +
            self.missing_information
        )


# ═══════════════════════════════════════════════════════
#  PLANNING AGENT SCHEMAS
# ═══════════════════════════════════════════════════════

class TaskItem(BaseModel):
    """A single actionable task in the plan."""
    task_id: str = Field(..., description="Unique task ID, e.g. T-001")
    title: str
    description: str
    supporting_fact_ids: list[str] = Field(default_factory=list)
    supporting_source_references: list[str] = Field(default_factory=list)
    owner: Optional[str] = Field(default=None)
    owner_confirmed: bool = Field(default=False, description="Whether the owner is confirmed from transcript")
    deadline: Optional[str] = Field(default=None)
    deadline_confirmed: bool = Field(default=False)
    priority: str = Field(default="medium", description="high, medium, low")
    dependencies: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    status: str = Field(default="proposed")
    evidence_classification: str = Field(
        default="supported",
        description="One of: supported, recommendation, unresolved"
    )
    open_questions: list[str] = Field(default_factory=list)


class RecommendationItem(BaseModel):
    """An explicit recommendation not directly supported by evidence."""
    rec_id: str
    title: str
    description: str
    rationale: str
    confidence: str = Field(default="low")


class UnresolvedQuestion(BaseModel):
    """A question that could not be resolved from the transcript."""
    question_id: str
    question: str
    context: str = ""
    related_fact_ids: list[str] = Field(default_factory=list)


class DependencyEdge(BaseModel):
    """A directed edge in the task dependency graph."""
    from_task: str
    to_task: str
    dependency_type: str = Field(default="blocks")


class ChangeItem(BaseModel):
    """A change made in a revised plan version."""
    change_id: str
    task_id: str
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: str


class PlanningOutput(BaseModel):
    """Validated output from the Planning Agent."""
    run_id: str
    source_version: int
    plan_version: int
    tasks: list[TaskItem] = Field(default_factory=list)
    supported_facts: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    unresolved_questions: list[UnresolvedQuestion] = Field(default_factory=list)
    dependency_graph: list[DependencyEdge] = Field(default_factory=list)
    change_summary: list[ChangeItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════
#  REVIEW AGENT SCHEMAS
# ═══════════════════════════════════════════════════════

class ReviewFinding(BaseModel):
    """A single finding from the Review Agent."""
    finding_id: str = Field(..., description="Unique finding ID, e.g. RF-001")
    severity: str = Field(..., description="critical, major, minor, info")
    category: str = Field(..., description="Category: unsupported_fact, rule_violation, missing_evidence, etc.")
    affected_id: str = Field(..., description="Task ID or fact ID affected")
    explanation: str
    evidence: str = Field(default="", description="Evidence or rule citation")
    required_correction: str = Field(default="")
    blocks_approval: bool = Field(default=False)


class ReviewOutput(BaseModel):
    """Validated output from the Review Agent."""
    run_id: str
    source_version: int
    plan_version: int
    outcome: str = Field(..., description="APPROVED, NEEDS_CORRECTION, or UNRESOLVED")
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
    open_questions: list[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════
#  API REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════

class CreateRunRequest(BaseModel):
    """Request body for POST /api/runs."""
    transcript: str = Field(..., min_length=10, max_length=50000)
    company_rules: str = Field(..., min_length=10, max_length=20000)
    name: Optional[str] = Field(default=None, max_length=200)
    title: Optional[str] = Field(default=None, max_length=200)
    fault_injection: Optional[str] = Field(
        default=None,
        description="Demo fault: intake_failure, schema_failure, planning_failure"
    )


class CorrectionRequest(BaseModel):
    """Request body for POST /api/runs/{run_id}/corrections."""
    fact_id: str
    field_name: str = Field(..., description="Field to correct, e.g. 'owner', 'deadline', 'content'")
    corrected_value: str = Field(..., max_length=5000)
    correction_note: str = Field(default="", max_length=5000)


class RunSummary(BaseModel):
    """Summary of a run for list views."""
    id: str
    name: Optional[str]
    status: str
    current_source_version: int
    current_plan_version: Optional[int]
    review_cycle_count: int
    created_at: str
    updated_at: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class RunDetail(RunSummary):
    """Full run detail including all outputs."""
    facts: list[dict] = Field(default_factory=list)
    current_plan: Optional[dict] = None
    latest_review: Optional[dict] = None
    corrections: list[dict] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    llm_provider: str = ""
    llm_model: str = ""
    llm_configured: bool = False
    demo_faults_enabled: bool = False
