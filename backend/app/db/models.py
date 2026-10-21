"""SQLAlchemy ORM models for the Operations Coordinator."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    Uuid,
    UniqueConstraint,
    Index,
)
from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    """Top-level workflow run."""

    __tablename__ = "runs"

    id = Column(String(36), primary_key=True)
    owner_id = Column(Uuid(as_uuid=False), nullable=True, index=True)
    name = Column(String(200), nullable=True)
    status = Column(String(50), nullable=False, default="CREATED")
    current_source_version = Column(Integer, nullable=False, default=1)
    current_plan_version = Column(Integer, nullable=True)
    review_cycle_count = Column(Integer, nullable=False, default=0)
    max_review_cycles = Column(Integer, nullable=False, default=2)
    fault_injection = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class SourceVersion(Base):
    """Versioned snapshot of transcript + company rules."""

    __tablename__ = "source_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    transcript = Column(Text, nullable=False)
    company_rules = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "version", name="uq_source_version"),
        Index("ix_source_run", "run_id"),
    )


class Fact(Base):
    """Extracted fact from the Intake Agent."""

    __tablename__ = "facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    source_version = Column(Integer, nullable=False)
    fact_id = Column(String(50), nullable=False)
    fact_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    evidence_quote = Column(Text, nullable=False)
    source_location = Column(String(200), nullable=False)
    confidence = Column(String(50), nullable=False)
    owner = Column(String(200), nullable=True)
    deadline = Column(String(200), nullable=True)
    missing_fields = Column(JSON, default=list)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_fact_run_sv", "run_id", "source_version"),
    )


class UserCorrection(Base):
    """User-submitted correction to an extracted fact."""

    __tablename__ = "user_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    fact_id = Column(String(50), nullable=False)
    field_name = Column(String(100), nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=False)
    correction_note = Column(Text, default="")
    new_source_version = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class AgentExecution(Base):
    """Record of a single agent execution attempt."""

    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    agent_type = Column(String(20), nullable=False)  # intake, planning, review
    step_id = Column(String(100), nullable=False, unique=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="running")
    started_at = Column(DateTime, default=_utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    input_snapshot = Column(JSON, nullable=True)
    output_snapshot = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    source_version = Column(Integer, nullable=False)
    plan_version = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_agent_run", "run_id", "agent_type"),
    )


class PlanVersion(Base):
    """A versioned action plan produced by the Planning Agent."""

    __tablename__ = "plan_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    source_version = Column(Integer, nullable=False)
    tasks = Column(JSON, nullable=False, default=list)
    supported_facts = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
    unresolved_questions = Column(JSON, nullable=False, default=list)
    dependency_graph = Column(JSON, nullable=False, default=list)
    change_summary = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "version", name="uq_plan_version"),
    )


class ReviewResult(Base):
    """Review outcome from the Review Agent."""

    __tablename__ = "review_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    plan_version = Column(Integer, nullable=False)
    source_version = Column(Integer, nullable=False)
    outcome = Column(String(50), nullable=False)
    findings = Column(JSON, nullable=False, default=list)
    summary = Column(Text, default="")
    open_questions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_review_run_pv", "run_id", "plan_version"),
    )


class WorkflowEvent(Base):
    """Chronological event in the workflow timeline."""

    __tablename__ = "workflow_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    agent_type = Column(String(20), nullable=True)
    description = Column(Text, nullable=False)
    version_info = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_event_run", "run_id"),)


class HandoffRecord(Base):
    """Record of a validated handoff between agents."""

    __tablename__ = "handoff_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    from_agent = Column(String(20), nullable=False)
    to_agent = Column(String(20), nullable=False)
    payload_summary = Column(Text, default="")
    payload = Column(JSON, nullable=True)
    source_version = Column(Integer, nullable=False)
    plan_version = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
