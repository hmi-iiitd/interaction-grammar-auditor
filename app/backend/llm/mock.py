"""
Mock LLM Provider — Returns template-based answers for testing
when no real LLM is available.
"""

from llm.provider import LLMProvider


class MockProvider(LLMProvider):
    def name(self) -> str:
        return "mock-template"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return (
            "This is a mock LLM response. The system is running in template mode. "
            "Connect a real LLM provider (e.g. NVIDIA NIM) for grounded explanations."
        )
