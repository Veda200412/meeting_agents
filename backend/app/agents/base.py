"""Base agent class with shared execution logic."""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Type

from pydantic import BaseModel
from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Abstract base for all LLM-powered agents.

    Each concrete agent must define:
    - agent_type: a short name like 'intake', 'planning', 'review'
    - system_prompt: the role-specific system prompt
    - build_user_prompt(): assembles the user prompt from inputs
    - output_model: the Pydantic model for the validated output
    """

    agent_type: str = ""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Role-specific system instructions."""
        ...

    @abstractmethod
    def build_user_prompt(self, **kwargs) -> str:
        """Build the user prompt from the agent's inputs."""
        ...

    @property
    @abstractmethod
    def output_model(self) -> Type[BaseModel]:
        """The Pydantic model class for the expected output."""
        ...

    def execute(self, **kwargs) -> BaseModel:
        """Run the agent: build prompt → call LLM → validate output."""
        user_prompt = self.build_user_prompt(**kwargs)

        logger.info("Executing %s agent", self.agent_type)

        result = self.provider.generate_structured(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            output_model=self.output_model,
        )

        logger.info("%s agent completed successfully", self.agent_type)
        return result
