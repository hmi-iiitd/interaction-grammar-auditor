"""
Reports router — generate and export reports.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pathlib import Path

from config import get_settings
from modules.loader import load_scenario, LoaderError
from modules.evidence_extractor import extract_all_evidence
from modules.report_generator import generate_markdown_report, generate_json_report
from modules.batch_runner import run_batch
from modules.explanation import generate_explanation
from llm.nim import NIMProvider

router = APIRouter()


@router.get("/{scenario_id}/markdown")
def get_markdown_report(scenario_id: str):
    """Generate and return a Markdown report for a scenario."""
    settings = get_settings()
    dataset_root = Path(settings.dataset_root)
    if not dataset_root.is_absolute():
        dataset_root = Path(__file__).parent.parent.parent / dataset_root

    try:
        scenario = load_scenario(str(dataset_root / scenario_id))
    except LoaderError as e:
        raise HTTPException(status_code=404, detail=str(e))

    evidence = extract_all_evidence(scenario.trace, scenario.audit_report)
    
    explanation = None
    try:
        nim_api_key = settings.nvidia_nim_api_key
        if nim_api_key:
            provider = NIMProvider(
                api_keys=[nim_api_key, settings.nvidia_nim_api_key_2],
                model=settings.llm_model,
                fallback_model=settings.llm_fallback_model,
                base_url=settings.nvidia_nim_base_url,
            )
            explanation = generate_explanation(
                llm=provider,
                scenario_id=scenario.scenario_id,
                metadata=scenario.metadata,
                audit_report=scenario.audit_report,
                trace_events=scenario.trace.get("events", [])
            )
    except Exception as e:
        print(f"Warning: Failed to generate LLM explanation: {e}")

    md = generate_markdown_report(scenario, evidence, explanation=explanation)
    return PlainTextResponse(md, media_type="text/markdown")


@router.get("/{scenario_id}/json")
def get_json_report(scenario_id: str):
    """Generate and return a JSON report for a scenario."""
    settings = get_settings()
    dataset_root = Path(settings.dataset_root)
    if not dataset_root.is_absolute():
        dataset_root = Path(__file__).parent.parent.parent / dataset_root

    try:
        scenario = load_scenario(str(dataset_root / scenario_id))
    except LoaderError as e:
        raise HTTPException(status_code=404, detail=str(e))

    evidence = extract_all_evidence(scenario.trace, scenario.audit_report)
    
    explanation = None
    try:
        nim_api_key = settings.nvidia_nim_api_key
        if nim_api_key:
            provider = NIMProvider(
                api_keys=[nim_api_key, settings.nvidia_nim_api_key_2],
                model=settings.llm_model,
                fallback_model=settings.llm_fallback_model,
                base_url=settings.nvidia_nim_base_url,
            )
            explanation = generate_explanation(
                llm=provider,
                scenario_id=scenario.scenario_id,
                metadata=scenario.metadata,
                audit_report=scenario.audit_report,
                trace_events=scenario.trace.get("events", [])
            )
    except Exception as e:
        print(f"Warning: Failed to generate LLM explanation: {e}")

    return generate_json_report(scenario, evidence, explanation=explanation)


@router.post("/batch")
def run_batch_reports():
    """Run batch report generation over all scenarios."""
    settings = get_settings()
    dataset_root = Path(settings.dataset_root)
    if not dataset_root.is_absolute():
        dataset_root = Path(__file__).parent.parent.parent / dataset_root

    return run_batch(str(dataset_root))
