"""Comprehensive tests for the AI Operations Coordinator backend.

Uses deterministic mock LLM responses — no API key needed.
"""

import json
import uuid
import os
import pytest
from unittest.mock import patch

# Set test environment BEFORE importing app modules
os.environ["SQLITE_TEST_DATABASE_URL"] = "sqlite:///./test_data/test_operations.db"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["GOOGLE_API_KEY"] = "test-key-not-real"
os.environ["ENABLE_DEMO_FAULTS"] = "true"
os.environ["TESTING"] = "true"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.api.auth import get_current_user
from app.db.database import Base, get_db
from app.db import repository as repo
from app.llm.schemas import (
    IntakeOutput, PlanningOutput, ReviewOutput,
    FactItem, TaskItem, ReviewFinding,
)
from app.orchestration.state_machine import validate_transition, InvalidTransitionError
from app.orchestration.handoffs import (
    validate_intake_to_planning, validate_planning_to_review,
    validate_review_output, HandoffValidationError,
)
from app.orchestration.workflow import execute_workflow, resume_workflow
from app.llm.provider import MockLLMProvider


# ── Test DB Setup ─────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_data/test_operations.db"
os.makedirs("./test_data", exist_ok=True)

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
TEST_USER_ID = "11111111-1111-4111-8111-111111111111"
app.dependency_overrides[get_current_user] = lambda: {"id": TEST_USER_ID}
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _get_db():
    return TestSession()


# ── Mock LLM Responses ───────────────────────────────

MOCK_INTAKE_RESPONSE = json.dumps({
    "run_id": "test",
    "source_version": 1,
    "decisions": [{
        "fact_id": "F-001",
        "fact_type": "decision",
        "content": "Prepare customer onboarding checklist before next review meeting",
        "evidence_quote": "the team agreed to prepare the customer onboarding checklist before the next review meeting",
        "source_location": "chars 30-120",
        "confidence": "explicit",
        "owner": "Priya",
        "deadline": None,
        "missing_fields": ["deadline"],
        "notes": "Deadline not specified for checklist preparation"
    }],
    "requirements": [{
        "fact_id": "F-002",
        "fact_type": "requirement",
        "content": "Engineering team must confirm API dependencies before implementation",
        "evidence_quote": "The engineering team must confirm the API dependencies before implementation starts",
        "source_location": "chars 130-220",
        "confidence": "explicit",
        "owner": None,
        "deadline": None,
        "missing_fields": ["owner", "deadline"],
        "notes": "No specific owner or deadline for API dependency review"
    }],
    "constraints": [],
    "action_items": [{
        "fact_id": "F-003",
        "fact_type": "action_item",
        "content": "Priya will draft the checklist",
        "evidence_quote": "Priya will draft the checklist",
        "source_location": "chars 121-150",
        "confidence": "explicit",
        "owner": "Priya",
        "deadline": None,
        "missing_fields": ["deadline"],
        "notes": ""
    }],
    "risks": [],
    "conflicts": [],
    "missing_information": [{
        "fact_id": "F-004",
        "fact_type": "missing_info",
        "content": "No exact deadline agreed for API dependency review",
        "evidence_quote": "No exact deadline was agreed for the API dependency review",
        "source_location": "chars 221-280",
        "confidence": "missing",
        "owner": None,
        "deadline": None,
        "missing_fields": ["owner", "deadline"],
        "notes": "Explicit acknowledgement that deadline is missing"
    }],
    "source_references": [{
        "ref_id": "SR-001",
        "quote": "the team agreed to prepare the customer onboarding checklist before the next review meeting",
        "location": "chars 30-120",
        "context": "operations meeting discussion"
    }]
})

MOCK_PLANNING_RESPONSE = json.dumps({
    "run_id": "test",
    "source_version": 1,
    "plan_version": 1,
    "tasks": [
        {
            "task_id": "T-001",
            "title": "Draft Customer Onboarding Checklist",
            "description": "Prepare the customer onboarding checklist before the next review meeting",
            "supporting_fact_ids": ["F-001", "F-003"],
            "supporting_source_references": ["SR-001"],
            "owner": "Priya",
            "owner_confirmed": True,
            "deadline": None,
            "deadline_confirmed": False,
            "priority": "high",
            "dependencies": [],
            "status": "proposed",
            "evidence_classification": "supported",
            "open_questions": []
        },
        {
            "task_id": "T-002",
            "title": "Confirm API Dependencies",
            "description": "Engineering team to review and confirm API dependencies before implementation",
            "supporting_fact_ids": ["F-002"],
            "supporting_source_references": [],
            "owner": None,
            "owner_confirmed": False,
            "deadline": None,
            "deadline_confirmed": False,
            "priority": "high",
            "dependencies": [],
            "status": "proposed",
            "evidence_classification": "supported",
            "open_questions": ["Who from the engineering team will lead this review?"]
        }
    ],
    "supported_facts": ["F-001", "F-002", "F-003"],
    "recommendations": [],
    "unresolved_questions": [{
        "question_id": "UQ-001",
        "question": "What is the deadline for the API dependency review?",
        "context": "No exact deadline was agreed in the meeting",
        "related_fact_ids": ["F-004"]
    }],
    "dependency_graph": [{
        "from_task": "T-001",
        "to_task": "T-002",
        "dependency_type": "blocks"
    }],
    "change_summary": []
})

MOCK_REVIEW_APPROVED_RESPONSE = json.dumps({
    "run_id": "test",
    "source_version": 1,
    "plan_version": 1,
    "outcome": "APPROVED",
    "findings": [{
        "finding_id": "RF-001",
        "severity": "info",
        "category": "missing_evidence",
        "affected_id": "T-002",
        "explanation": "API dependency review has no confirmed owner",
        "evidence": "No owner was specified in the transcript",
        "required_correction": "None - correctly marked as unconfirmed",
        "blocks_approval": False
    }],
    "summary": "Plan correctly represents the meeting decisions with appropriate uncertainty markers.",
    "open_questions": ["What is the deadline for the API dependency review?"]
})

MOCK_REVIEW_CORRECTION_RESPONSE = json.dumps({
    "run_id": "test",
    "source_version": 1,
    "plan_version": 1,
    "outcome": "NEEDS_CORRECTION",
    "findings": [{
        "finding_id": "RF-001",
        "severity": "critical",
        "category": "rule_violation",
        "affected_id": "T-001",
        "explanation": "Task has an invented deadline not present in transcript",
        "evidence": "Rule: Do not invent exact deadlines",
        "required_correction": "Remove the unconfirmed deadline or mark deadline_confirmed as false",
        "blocks_approval": True
    }],
    "summary": "Plan contains a rule violation that must be corrected.",
    "open_questions": []
})


# ═══════════════════════════════════════════════════════
#  1. SCHEMA VALIDATION TESTS
# ═══════════════════════════════════════════════════════

class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_intake_output_valid(self):
        data = json.loads(MOCK_INTAKE_RESPONSE)
        output = IntakeOutput.model_validate(data)
        assert output.run_id == "test"
        assert len(output.decisions) == 1
        assert output.decisions[0].fact_id == "F-001"

    def test_intake_output_missing_evidence(self):
        data = json.loads(MOCK_INTAKE_RESPONSE)
        data["decisions"][0]["evidence_quote"] = ""
        # Should still validate (empty string is allowed by schema)
        output = IntakeOutput.model_validate(data)
        assert output.decisions[0].evidence_quote == ""

    def test_planning_output_valid(self):
        data = json.loads(MOCK_PLANNING_RESPONSE)
        output = PlanningOutput.model_validate(data)
        assert len(output.tasks) == 2
        assert output.tasks[0].owner_confirmed is True

    def test_review_output_valid(self):
        data = json.loads(MOCK_REVIEW_APPROVED_RESPONSE)
        output = ReviewOutput.model_validate(data)
        assert output.outcome == "APPROVED"

    def test_fact_item_null_owner(self):
        fact = FactItem(
            fact_id="F-100", fact_type="requirement",
            content="Test", evidence_quote="test quote",
            source_location="line 1", confidence="explicit",
        )
        assert fact.owner is None
        assert fact.deadline is None

    def test_task_item_defaults(self):
        task = TaskItem(
            task_id="T-100", title="Test", description="desc",
        )
        assert task.owner_confirmed is False
        assert task.deadline_confirmed is False
        assert task.priority == "medium"


# ═══════════════════════════════════════════════════════
#  2. HANDOFF VALIDATION TESTS
# ═══════════════════════════════════════════════════════

class TestHandoffValidation:
    """Test handoff validation between agents."""

    def test_valid_intake_to_planning(self):
        data = json.loads(MOCK_INTAKE_RESPONSE)
        result = validate_intake_to_planning(data)
        assert isinstance(result, IntakeOutput)

    def test_intake_missing_evidence_rejects(self):
        data = json.loads(MOCK_INTAKE_RESPONSE)
        data["decisions"][0]["evidence_quote"] = ""
        with pytest.raises(HandoffValidationError, match="missing evidence_quote"):
            validate_intake_to_planning(data)

    def test_valid_planning_to_review(self):
        data = json.loads(MOCK_PLANNING_RESPONSE)
        result = validate_planning_to_review(data)
        assert isinstance(result, PlanningOutput)

    def test_planning_duplicate_task_ids(self):
        data = json.loads(MOCK_PLANNING_RESPONSE)
        data["tasks"][1]["task_id"] = "T-001"  # duplicate
        with pytest.raises(HandoffValidationError, match="Duplicate task IDs"):
            validate_planning_to_review(data)

    def test_planning_invalid_dependency(self):
        data = json.loads(MOCK_PLANNING_RESPONSE)
        data["tasks"][0]["dependencies"] = ["T-999"]  # non-existent
        with pytest.raises(HandoffValidationError, match="unknown task"):
            validate_planning_to_review(data)

    def test_planning_dependency_cycle(self):
        data = json.loads(MOCK_PLANNING_RESPONSE)
        data["tasks"][0]["dependencies"] = ["T-002"]
        data["tasks"][1]["dependencies"] = ["T-001"]  # creates cycle
        with pytest.raises(HandoffValidationError, match="cycle"):
            validate_planning_to_review(data)

    def test_valid_review_output(self):
        data = json.loads(MOCK_REVIEW_APPROVED_RESPONSE)
        result = validate_review_output(data)
        assert result.outcome == "APPROVED"

    def test_review_invalid_outcome(self):
        data = json.loads(MOCK_REVIEW_APPROVED_RESPONSE)
        data["outcome"] = "INVALID"
        with pytest.raises(HandoffValidationError, match="Invalid review outcome"):
            validate_review_output(data)


# ═══════════════════════════════════════════════════════
#  3. STATE MACHINE TESTS
# ═══════════════════════════════════════════════════════

class TestStateMachine:
    """Test workflow state transitions."""

    def test_valid_transitions(self):
        assert validate_transition("CREATED", "INTAKE_RUNNING")
        assert validate_transition("INTAKE_RUNNING", "INTAKE_COMPLETED")
        assert validate_transition("INTAKE_COMPLETED", "PLANNING_RUNNING")
        assert validate_transition("REVIEW_RUNNING", "APPROVED")
        assert validate_transition("REVIEW_RUNNING", "NEEDS_CORRECTION")
        assert validate_transition("NEEDS_CORRECTION", "PLANNING_RUNNING")

    def test_invalid_transitions(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("CREATED", "APPROVED")
        with pytest.raises(InvalidTransitionError):
            validate_transition("APPROVED", "CREATED")
        with pytest.raises(InvalidTransitionError):
            validate_transition("INTAKE_RUNNING", "REVIEW_RUNNING")

    def test_failed_can_resume(self):
        assert validate_transition("FAILED", "INTAKE_RUNNING")
        assert validate_transition("FAILED", "PLANNING_RUNNING")


# ═══════════════════════════════════════════════════════
#  4. API ENDPOINT TESTS
# ═══════════════════════════════════════════════════════

class TestAPI:
    """Test FastAPI endpoints."""

    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_get_samples(self):
        resp = client.get("/api/samples")
        assert resp.status_code == 200
        data = resp.json()
        assert "simple" in data["transcripts"]
        assert "complex" in data["transcripts"]

    def test_create_run(self):
        resp = client.post("/api/runs", json={
            "transcript": "Test meeting transcript with enough content to pass validation.",
            "company_rules": "Rule 1: Follow all rules. Rule 2: Document everything properly.",
            "name": "Test Run",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "CREATED"
        with TestSession() as db:
            run = repo.get_run(db, data["id"])
            assert run.owner_id == TEST_USER_ID

    def test_create_run_validation(self):
        resp = client.post("/api/runs", json={
            "transcript": "short",
            "company_rules": "short",
        })
        assert resp.status_code == 422  # Validation error

    def test_list_runs(self):
        # Create a run first
        client.post("/api/runs", json={
            "transcript": "Test transcript for listing runs in the system.",
            "company_rules": "Company rules for testing the list endpoint.",
        })
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_get_run(self):
        create = client.post("/api/runs", json={
            "transcript": "Test transcript for getting run details and info.",
            "company_rules": "Rules for testing get run endpoint functionality.",
        })
        run_id = create.json()["id"]
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == run_id

    def test_get_nonexistent_run(self):
        resp = client.get(f"/api/runs/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_run_is_hidden_from_other_authenticated_user(self):
        create = client.post("/api/runs", json={
            "transcript": "Private transcript owned by the first test user.",
            "company_rules": "Private rules owned by the first test user.",
        })
        run_id = create.json()["id"]
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "22222222-2222-4222-8222-222222222222"
        }
        try:
            assert client.get(f"/api/runs/{run_id}").status_code == 404
            assert client.get("/api/runs").json() == []
            assert client.post(f"/api/runs/{run_id}/reset").status_code == 404
        finally:
            app.dependency_overrides[get_current_user] = lambda: {"id": TEST_USER_ID}

    def test_run_api_requires_authentication(self):
        app.dependency_overrides.pop(get_current_user)
        try:
            assert client.get("/api/runs").status_code == 401
        finally:
            app.dependency_overrides[get_current_user] = lambda: {"id": TEST_USER_ID}

    def test_get_events_empty(self):
        create = client.post("/api/runs", json={
            "transcript": "Test transcript for events endpoint testing here.",
            "company_rules": "Rules for testing the events listing endpoint.",
        })
        run_id = create.json()["id"]
        resp = client.get(f"/api/runs/{run_id}/events")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_reset_run(self):
        create = client.post("/api/runs", json={
            "transcript": "Test transcript for reset functionality testing.",
            "company_rules": "Rules for testing the reset run endpoint here.",
        })
        run_id = create.json()["id"]
        resp = client.post(f"/api/runs/{run_id}/reset")
        assert resp.status_code == 200
        # Verify run is gone
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 404

    def test_correction_no_facts(self):
        create = client.post("/api/runs", json={
            "transcript": "Test transcript for correction with no facts present.",
            "company_rules": "Rules for testing fact corrections when empty.",
        })
        run_id = create.json()["id"]
        resp = client.post(f"/api/runs/{run_id}/corrections", json={
            "fact_id": "F-001",
            "field_name": "owner",
            "corrected_value": "Priya",
        })
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════
#  5. REPOSITORY TESTS
# ═══════════════════════════════════════════════════════

class TestRepository:
    """Test local repository behavior and Data API integration."""

    def test_create_and_get_run(self):
        db = _get_db()
        try:
            run = repo.create_run(db, str(uuid.uuid4()), "Test",
                                  "Transcript", "Rules")
            assert run.status == "CREATED"
            fetched = repo.get_run(db, run.id)
            assert fetched is not None
            assert fetched.name == "Test"
        finally:
            db.close()

    def test_source_versioning(self):
        db = _get_db()
        try:
            run_id = str(uuid.uuid4())
            repo.create_run(db, run_id, "Test", "Transcript v1", "Rules")
            sv1 = repo.get_source_version(db, run_id, 1)
            assert sv1.transcript == "Transcript v1"

            repo.create_source_version(db, run_id, 2, "Transcript v2", "Rules v2")
            sv2 = repo.get_source_version(db, run_id, 2)
            assert sv2.transcript == "Transcript v2"

            # v1 still exists
            sv1_again = repo.get_source_version(db, run_id, 1)
            assert sv1_again.transcript == "Transcript v1"
        finally:
            db.close()

    def test_run_isolation(self):
        db = _get_db()
        try:
            run1_id = str(uuid.uuid4())
            run2_id = str(uuid.uuid4())
            repo.create_run(db, run1_id, "Run 1", "Transcript 1", "Rules 1")
            repo.create_run(
                db, run2_id, "Run 2", "Transcript 2", "Rules 2",
                owner_id="22222222-2222-4222-8222-222222222222",
            )

            facts1 = repo.get_facts(db, run1_id, 1)
            facts2 = repo.get_facts(db, run2_id, 1)
            assert facts1 == []
            assert facts2 == []

            repo.save_facts(db, run1_id, 1, [{
                "fact_id": "F-001", "fact_type": "decision",
                "content": "Run 1 fact", "evidence_quote": "quote",
                "source_location": "line 1", "confidence": "explicit",
            }])

            facts1 = repo.get_facts(db, run1_id, 1)
            facts2 = repo.get_facts(db, run2_id, 1)
            assert len(facts1) == 1
            assert len(facts2) == 0  # Isolation
        finally:
            db.close()

    def test_invalidate_downstream(self):
        db = _get_db()
        try:
            run_id = str(uuid.uuid4())
            repo.create_run(db, run_id, "Test", "Transcript", "Rules")

            # Save some facts
            repo.save_facts(db, run_id, 1, [{
                "fact_id": "F-001", "fact_type": "decision",
                "content": "Test", "evidence_quote": "quote",
                "source_location": "line 1", "confidence": "explicit",
            }])

            # Invalidate
            repo.invalidate_downstream(db, run_id)

            facts = repo.get_facts(db, run_id, 1)
            assert len(facts) == 0

            run = repo.get_run(db, run_id)
            assert run.status == "CREATED"
            assert run.current_plan_version is None
        finally:
            db.close()

    def test_idempotent_step(self):
        db = _get_db()
        try:
            run_id = str(uuid.uuid4())
            repo.create_run(db, run_id, "Test", "Transcript", "Rules")

            step_id = f"{run_id}:intake:sv1:pv0"
            repo.create_execution(db, run_id, "intake", step_id, 1)
            repo.complete_execution(db, step_id, output_snapshot={"test": True})

            # Should find the completed step
            existing = repo.get_completed_step(db, step_id)
            assert existing is not None
            assert existing.output_snapshot == {"test": True}
        finally:
            db.close()


# ═══════════════════════════════════════════════════════
#  6. WORKFLOW TESTS (with Mock LLM)
# ═══════════════════════════════════════════════════════

class TestWorkflow:
    """Test the full workflow with deterministic mock LLM."""

    def _create_mock_provider(self):
        """Create a mock provider with preset responses."""
        provider = MockLLMProvider()
        provider.set_response("Intake Agent", MOCK_INTAKE_RESPONSE)
        provider.set_response("Planning Agent", MOCK_PLANNING_RESPONSE)
        provider.set_response("Review Agent", MOCK_REVIEW_APPROVED_RESPONSE)
        return provider

    def test_full_approved_workflow(self):
        db = _get_db()
        try:
            run_id = str(uuid.uuid4())
            repo.create_run(
                db, run_id, "Test Workflow",
                "During the operations meeting, the team agreed to prepare the "
                "customer onboarding checklist before the next review meeting. "
                "Priya will draft the checklist.",
                "Only confirmed owners may be treated as confirmed.",
                owner_id=TEST_USER_ID,
            )

            provider = self._create_mock_provider()
            execute_workflow(run_id, db, provider)

            run = repo.get_run(db, run_id)
            assert run.status == "APPROVED"

            # Check that all three agents executed
            execs = repo.get_executions(db, run_id)
            agent_types = [e.agent_type for e in execs if e.status == "completed"]
            assert "intake" in agent_types
            assert "planning" in agent_types
            assert "review" in agent_types

            handoffs = repo.get_handoffs(db, run_id)
            assert [(h.from_agent, h.to_agent) for h in handoffs] == [
                ("intake", "planning"),
                ("planning", "review"),
            ]
            assert handoffs[0].payload["source_version"] == 1
            assert handoffs[1].payload["plan_version"] == 1

            response = client.get(f"/api/runs/{run_id}/handoffs")
            assert response.status_code == 200
            api_handoffs = response.json()
            assert api_handoffs[0]["payload"]["source_version"] == 1
            assert api_handoffs[1]["payload"]["plan_version"] == 1
        finally:
            db.close()

    def test_correction_loop_workflow(self):
        db = _get_db()
        try:
            run_id = str(uuid.uuid4())
            repo.create_run(
                db, run_id, "Correction Test",
                "Test transcript content for the correction loop testing.",
                "Do not invent deadlines."
            )

            provider = MockLLMProvider()
            provider.set_response("Intake Agent", MOCK_INTAKE_RESPONSE)
            provider.set_response("Planning Agent", MOCK_PLANNING_RESPONSE)
            # First review: needs correction, second: approved
            call_count = [0]
            original_generate = provider.generate

            def counting_generate(system_prompt, user_prompt, schema=None):
                if "You are the Review Agent" in system_prompt:
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return MOCK_REVIEW_CORRECTION_RESPONSE
                    else:
                        return MOCK_REVIEW_APPROVED_RESPONSE
                return original_generate(system_prompt, user_prompt, schema)

            provider.generate = counting_generate

            execute_workflow(run_id, db, provider)

            run = repo.get_run(db, run_id)
            assert run.status == "APPROVED"

            # Should have 2 plan versions
            plans = repo.get_all_plans(db, run_id)
            assert len(plans) == 2

            feedback_handoffs = [
                handoff for handoff in repo.get_handoffs(db, run_id)
                if handoff.from_agent == "review"
                and handoff.to_agent == "planning"
            ]
            assert len(feedback_handoffs) == 1
            assert feedback_handoffs[0].payload["outcome"] == "NEEDS_CORRECTION"
            assert feedback_handoffs[0].payload["findings"]
        finally:
            db.close()

    def test_demo_fault_intake(self):
        db = _get_db()
        try:
            run_id = str(uuid.uuid4())
            repo.create_run(
                db, run_id, "Fault Test",
                "Test transcript for fault injection testing scenario.",
                "Test rules for demo fault simulation testing.",
            )
            repo.set_run_fault(db, run_id, "intake_failure")

            provider = self._create_mock_provider()
            execute_workflow(run_id, db, provider)

            run = repo.get_run(db, run_id)
            assert run.status == "FAILED"
            assert "SIMULATED" in (run.error_message or "")
        finally:
            db.close()

    def test_resume_after_fault(self):
        db = _get_db()
        try:
            run_id = str(uuid.uuid4())
            repo.create_run(
                db, run_id, "Resume Test",
                "Test transcript for resume after fault testing here.",
                "Test rules for resume functionality verification.",
            )
            repo.set_run_fault(db, run_id, "intake_failure")

            provider = self._create_mock_provider()
            execute_workflow(run_id, db, provider)

            run = repo.get_run(db, run_id)
            assert run.status == "FAILED"

            # Resume (clears fault)
            resume_workflow(run_id, db, provider)

            run = repo.get_run(db, run_id)
            assert run.status == "APPROVED"
        finally:
            db.close()


# ═══════════════════════════════════════════════════════
#  7. SECURITY TESTS
# ═══════════════════════════════════════════════════════

class TestSecurity:
    """Test security controls."""

    def test_health_no_secrets(self):
        resp = client.get("/api/health")
        body = resp.text
        assert "test-key-not-real" not in body

    def test_input_size_limits(self):
        resp = client.post("/api/runs", json={
            "transcript": "x" * 5,  # too short
            "company_rules": "y" * 5,
        })
        assert resp.status_code == 422

    def test_cross_run_access(self):
        # Create two runs
        r1 = client.post("/api/runs", json={
            "transcript": "Run 1 transcript with enough content for validation.",
            "company_rules": "Run 1 rules with sufficient content for validation.",
        }).json()
        r2 = client.post("/api/runs", json={
            "transcript": "Run 2 transcript with different content and context.",
            "company_rules": "Run 2 rules with different policies and guidelines.",
        }).json()

        # Each run should have its own data
        d1 = client.get(f"/api/runs/{r1['id']}").json()
        d2 = client.get(f"/api/runs/{r2['id']}").json()
        assert d1["id"] != d2["id"]
