"""
NVIDIA NIM LLM Provider — Uses the OpenAI-compatible API.

Supports key rotation: if the primary key fails (rate limit, 403),
it automatically retries with the fallback key.
"""

import logging
from openai import OpenAI

from llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class NIMProvider(LLMProvider):
    def __init__(
        self,
        api_keys: list[str],
        model: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        fallback_model: str | None = None,
    ):
        self.api_keys = [k for k in api_keys if k]  # filter empty
        self.model = model
        self.fallback_model = fallback_model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._current_key_idx = 0

        if not self.api_keys:
            raise ValueError("At least one NIM API key is required")

    def name(self) -> str:
        return f"NIM:{self.model}"

    def _get_client(self) -> OpenAI:
        return OpenAI(
            base_url=self.base_url,
            api_key=self.api_keys[self._current_key_idx],
        )

    def _call(self, system_prompt: str, user_prompt: str, model: str) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate with automatic key rotation and model fallback.
        
        Tries: primary key + primary model
             → fallback key + primary model
             → primary key + fallback model
        """
        errors = []

        # Try each key with primary model
        for attempt in range(len(self.api_keys)):
            try:
                logger.info(f"NIM call: model={self.model}, key_idx={self._current_key_idx}")
                result = self._call(system_prompt, user_prompt, self.model)
                logger.info(f"NIM success: {len(result)} chars")
                return result
            except Exception as e:
                errors.append(f"key_{self._current_key_idx}/{self.model}: {e}")
                logger.warning(f"NIM key {self._current_key_idx} failed: {e}")
                self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)

        # Try fallback model if available
        if self.fallback_model and self.fallback_model != self.model:
            for attempt in range(len(self.api_keys)):
                try:
                    logger.info(f"NIM fallback: model={self.fallback_model}, key_idx={self._current_key_idx}")
                    result = self._call(system_prompt, user_prompt, self.fallback_model)
                    logger.info(f"NIM fallback success: {len(result)} chars")
                    return result
                except Exception as e:
                    errors.append(f"key_{self._current_key_idx}/{self.fallback_model}: {e}")
                    logger.warning(f"NIM fallback key {self._current_key_idx} failed: {e}")
                    self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)

        error_detail = "; ".join(errors)
        raise RuntimeError(f"All NIM attempts failed: {error_detail}")
