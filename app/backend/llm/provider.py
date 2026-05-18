"""
LLM Provider — Abstract interface for LLM backends.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response given system and user prompts."""
        pass

    @abstractmethod
    def name(self) -> str:
        """Return the provider name for logging."""
        pass
