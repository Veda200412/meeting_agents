"""LLM provider abstraction with Gemini implementation.

Design: The abstract LLMProvider interface allows swapping providers
without changing the agent or orchestration code.
"""

from __future__ import annotations
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError
from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(Exception):
    """Raised when the LLM provider fails."""
    pass


class LLMSchemaError(Exception):
    """Raised when the LLM response fails schema validation."""
    pass


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str,
                 response_schema: dict | None = None) -> str:
        """Send a prompt and return the raw text response."""
        ...

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: Type[T],
        max_retries: int = 2,
    ) -> T:
        """Generate a structured response validated against a Pydantic model.

        Retries on JSON parse or validation errors (not on API failures,
        which are retried at the provider level).
        """
        last_error = None
        for attempt in range(1, max_retries + 2):  # +1 for the initial attempt
            try:
                schema_dict = output_model.model_json_schema()
                raw = self.generate(system_prompt, user_prompt, schema_dict)

                # Try to extract JSON from the response
                json_str = self._extract_json(raw)
                data = json.loads(json_str)
                return output_model.model_validate(data)

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                logger.warning(
                    "Schema validation attempt %d/%d failed: %s",
                    attempt, max_retries + 1, str(e)[:200],
                )
                if attempt <= max_retries:
                    time.sleep(0.5 * attempt)
                continue

        raise LLMSchemaError(
            f"Failed to get valid structured output after {max_retries + 1} attempts. "
            f"Last error: {str(last_error)[:300]}"
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from text that may contain markdown fences."""
        text = text.strip()
        if text.startswith("```"):
            # Remove markdown code fences
            lines = text.split("\n")
            # Remove first and last fence lines
            start = 1 if lines[0].startswith("```") else 0
            end = -1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[start:end]).strip()
        return text


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self):
        settings = get_settings()
        if not settings.GOOGLE_API_KEY:
            raise LLMProviderError(
                "GOOGLE_API_KEY is not configured. "
                "Set it in your .env file to use the Gemini provider."
            )

        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        self._model_name = settings.LLM_MODEL
        self._max_retries = settings.LLM_MAX_RETRIES
        self._timeout = settings.REQUEST_TIMEOUT_SECONDS

        self._model = genai.GenerativeModel(
            self._model_name,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

    def generate(self, system_prompt: str, user_prompt: str,
                 response_schema: dict | None = None) -> str:
        """Call Gemini API with retries and exponential backoff."""
        import google.generativeai as genai
        from google.api_core import exceptions as google_exceptions

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        if response_schema:
            full_prompt += (
                "\n\nRespond ONLY with valid JSON matching this schema. "
                "Do not include any text outside the JSON object.\n"
                f"Schema: {json.dumps(response_schema, indent=2)}"
            )

        last_error = None
        for attempt in range(1, self._max_retries + 2):
            try:
                response = self._model.generate_content(full_prompt)

                if not response.text:
                    raise LLMProviderError("Empty response from Gemini API")

                return response.text

            except (google_exceptions.ResourceExhausted,
                    google_exceptions.ServiceUnavailable,
                    google_exceptions.DeadlineExceeded) as e:
                last_error = e
                if attempt <= self._max_retries:
                    wait = min(2 ** attempt, 30)
                    logger.warning(
                        "Gemini API transient error (attempt %d/%d), retrying in %ds: %s",
                        attempt, self._max_retries + 1, wait, str(e)[:100],
                    )
                    time.sleep(wait)
                continue
            except Exception as e:
                # Non-transient errors should not be retried
                raise LLMProviderError(f"Gemini API error: {str(e)[:300]}") from e

        raise LLMProviderError(
            f"Gemini API failed after {self._max_retries + 1} attempts. "
            f"Last error: {str(last_error)[:300]}"
        )


DEFAULT_MOCK_RESPONSES = {
    "Intake Agent": json.dumps({
        "run_id": "mock_run",
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
    }),
    "Planning Agent": json.dumps({
        "run_id": "mock_run",
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
        "recommendations": [{
            "rec_id": "REC-001",
            "title": "Schedule API Architecture Sync",
            "description": "Hold a 30-minute sync between Priya and the Engineering Lead to lock the API spec",
            "rationale": "Mitigates dependency delay before checklist finalization",
            "confidence": "high"
        }],
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
    }),
    "Review Agent": json.dumps({
        "run_id": "mock_run",
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
        "summary": "Plan correctly represents meeting decisions with appropriate uncertainty markers and respects company rules.",
        "open_questions": ["What is the deadline for the API dependency review?"]
    })
}


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM for testing and out-of-the-box demonstration."""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses if responses is not None else dict(DEFAULT_MOCK_RESPONSES)
        self._call_count = 0
        self._calls: list[dict] = []

    def generate(self, system_prompt: str, user_prompt: str,
                 response_schema: dict | None = None) -> str:
        self._call_count += 1
        self._calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "schema": response_schema,
        })

        # Check for agent role in system prompt first (e.g. "You are the Planning Agent")
        for key, response in self._responses.items():
            if f"You are the {key}" in system_prompt:
                return response

        # Next check for exact key in system prompt
        for key, response in self._responses.items():
            if key in system_prompt:
                return response

        # Finally check user prompt
        for key, response in self._responses.items():
            if key in user_prompt:
                return response

        # Default: return empty JSON matching common patterns
        return '{"error": "No mock response configured"}'

    def set_response(self, key: str, response: str) -> None:
        self._responses[key] = response


def create_provider(provider_name: str | None = None) -> LLMProvider:
    """Factory function to create an LLM provider."""
    settings = get_settings()
    name = (provider_name or settings.LLM_PROVIDER).lower()

    if name == "gemini":
        return GeminiProvider()
    elif name == "mock":
        return MockLLMProvider()
    else:
        raise LLMProviderError(f"Unknown LLM provider: {name}")
