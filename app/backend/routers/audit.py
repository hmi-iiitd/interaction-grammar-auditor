"""
Audit router — evidence extraction and audit details.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path

from config import get_settings
from modules.loader import load_scenario, LoaderError
from modules.evidence_extractor import extract_all_evidence

router = APIRouter()


@router.get("/{scenario_id}")
def get_audit_details(scenario_id: str):
    """Get audit details with evidence segments for a scenario."""
    settings = get_settings()
    dataset_root = Path(settings.dataset_root)
    if not dataset_root.is_absolute():
        dataset_root = Path(__file__).parent.parent.parent / dataset_root

    try:
        scenario = load_scenario(str(dataset_root / scenario_id))
    except LoaderError as e:
        raise HTTPException(status_code=404, detail=str(e))

    evidence = extract_all_evidence(scenario.trace, scenario.audit_report)

    return {
        "scenario_id": scenario_id,
        "verdict": scenario.audit_report["verdict"],
        "violations": scenario.audit_report.get("violations", []),
        "counterexample": scenario.counterexample,
        "evidence": evidence,
        "trace": scenario.trace,
    }
