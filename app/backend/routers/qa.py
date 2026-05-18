"""
Q&A router — Grounded Q&A using LLM (Module F).
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from config import get_settings
from modules.loader import load_scenario, LoaderError
from modules.grounded_qa import answer_question

logger = logging.getLogger(__name__)

router = APIRouter()

# LLM provider (initialized lazily)
_llm = None


def _get_llm():
    """Lazy-initialize the LLM provider."""
    global _llm
    if _llm is not None:
        return _llm

    settings = get_settings()
    keys = [settings.nvidia_nim_api_key, settings.nvidia_nim_api_key_2]
    keys = [k for k in keys if k]

    if keys:
        try:
            from llm.nim import NIMProvider
            _llm = NIMProvider(
                api_keys=keys,
                model=settings.llm_model,
                base_url=settings.nvidia_nim_base_url,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                fallback_model=settings.llm_fallback_model,
            )
            logger.info(f"NIM provider initialized: {_llm.name()}")
            return _llm
        except Exception as e:
            logger.warning(f"Failed to init NIM provider: {e}")

    from llm.mock import MockProvider
    _llm = MockProvider()
    logger.info("Using mock LLM provider (no API keys)")
    return _llm


class QARequest(BaseModel):
    scenario_id: str
    question: str


@router.post("")
def ask_question_endpoint(req: QARequest):
    """Answer a grounded question about a scenario using the LLM."""
    settings = get_settings()
    dataset_root = Path(settings.dataset_root)
    if not dataset_root.is_absolute():
        dataset_root = Path(__file__).parent.parent.parent / dataset_root

    try:
        scenario = load_scenario(str(dataset_root / req.scenario_id))
    except LoaderError as e:
        raise HTTPException(status_code=404, detail=str(e))

    llm = _get_llm()
    result = answer_question(llm, req.question, scenario)

    return {
        "scenario_id": req.scenario_id,
        "question": req.question,
        **result,
    }
