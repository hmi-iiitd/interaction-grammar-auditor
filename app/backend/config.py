"""
Backend configuration using pydantic-settings.
Reads from .env file in the app/ root.
"""

from pathlib import Path
from functools import lru_cache

# Try pydantic-settings, fallback to manual .env parsing
try:
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        nvidia_nim_api_key: str = ""
        nvidia_nim_api_key_2: str = ""
        nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
        llm_model: str = "deepseek-ai/deepseek-v4-flash"
        llm_fallback_model: str = "nvidia/nemotron-3-super-120b-a12b"
        llm_temperature: float = 0.1
        llm_max_tokens: int = 4096
        dataset_root: str = "./dataset"
        backend_port: int = 8000
        frontend_port: int = 5173

        class Config:
            env_file = str(Path(__file__).parent.parent / ".env")
            env_file_encoding = "utf-8"
            extra = "ignore"

except ImportError:
    import os

    class Settings:
        """Fallback settings from environment variables."""
        def __init__(self):
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        os.environ.setdefault(key.strip(), val.strip())

            self.nvidia_nim_api_key = os.getenv("NVIDIA_NIM_API_KEY", "")
            self.nvidia_nim_api_key_2 = os.getenv("NVIDIA_NIM_API_KEY_2", "")
            self.nvidia_nim_base_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
            self.llm_model = os.getenv("LLM_MODEL", "deepseek-ai/deepseek-v4-flash")
            self.llm_fallback_model = os.getenv("LLM_FALLBACK_MODEL", "nvidia/nemotron-3-super-120b-a12b")
            self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
            self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
            self.dataset_root = os.getenv("DATASET_ROOT", "./dataset")
            self.backend_port = int(os.getenv("BACKEND_PORT", "8000"))


@lru_cache()
def get_settings() -> Settings:
    return Settings()
