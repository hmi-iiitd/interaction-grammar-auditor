"""
Scenarios router — list and load scenarios from the dataset.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path

from config import get_settings
from modules.loader import load_scenario, load_all_scenarios, LoaderError
from modules.schema_validator import validate_scenario
from modules.upload_handler import handle_upload, validate_contract_file, UploadError

router = APIRouter()

@router.post("/upload")
async def upload_scenario(
    scenario_id: str = Form(...),
    interaction_type: str = Form("Turn-taking / acknowledgment"),
    robot_platform: str = Form("NAO"),
    contract_file: UploadFile = File(None),
    contract_text: str = Form(None),
    trace_file: UploadFile = File(...)
):
    """Upload and process a new scenario."""
    try:
        result = handle_upload(
            scenario_id=scenario_id,
            contract_file=contract_file,
            contract_text=contract_text,
            trace_file=trace_file,
            interaction_type=interaction_type,
            robot_platform=robot_platform
        )
        return result
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/validate-contract")
async def validate_contract(
    contract_file: UploadFile = File(None),
    contract_text: str = Form(None)
):
    """Validate a contract file independently."""
    try:
        return validate_contract_file(contract_file, contract_text)
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("")
def list_scenarios():
    """List all scenarios with their verdicts and metadata."""
    settings = get_settings()
    dataset_root = Path(settings.dataset_root)
    if not dataset_root.is_absolute():
        dataset_root = Path(__file__).parent.parent.parent / dataset_root

    try:
        scenarios = load_all_scenarios(str(dataset_root))
    except LoaderError as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = []
    for s in scenarios:
        audit = s.audit_report
        violations = audit.get("violations", [])
        violation_types = list({v["violated_operator"] for v in violations})

        result.append({
            "scenario_id": s.scenario_id,
            "interaction_type": s.metadata.get("interaction_type", ""),
            "robot_platform": s.metadata.get("robot_platform", ""),
            "contract_id": audit.get("contract_id", ""),
            "verdict": audit["verdict"],
            "num_events": audit.get("num_events", 0),
            "num_violations": audit.get("num_violations", 0),
            "violation_types": violation_types,
            "description": _scenario_description(s),
        })

    # Aggregate stats
    total = len(result)
    sat = sum(1 for r in result if r["verdict"] == "SAT")
    unsat = total - sat

    all_violations = []
    for r in result:
        all_violations.extend(r["violation_types"])
    most_common = max(set(all_violations), key=all_violations.count) if all_violations else "—"

    return {
        "scenarios": result,
        "stats": {
            "total": total,
            "sat": sat,
            "unsat": unsat,
            "most_common_violation": most_common,
        },
    }


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str):
    """Get full details for a single scenario."""
    settings = get_settings()
    dataset_root = Path(settings.dataset_root)
    if not dataset_root.is_absolute():
        dataset_root = Path(__file__).parent.parent.parent / dataset_root

    scenario_path = dataset_root / scenario_id
    try:
        scenario = load_scenario(str(scenario_path))
    except LoaderError as e:
        raise HTTPException(status_code=404, detail=str(e))

    errors = validate_scenario(scenario)

    return {
        "scenario_id": scenario.scenario_id,
        "metadata": scenario.metadata,
        "trace": scenario.trace,
        "contract": scenario.contract,
        "audit_report": scenario.audit_report,
        "counterexample": scenario.counterexample,
        "validation_errors": errors,
    }


def _scenario_description(scenario) -> str:
    """Generate a brief human-readable description."""
    verdict = scenario.audit_report["verdict"]
    violations = scenario.audit_report.get("violations", [])

    if verdict == "SAT":
        return "Interaction completed successfully"

    if violations:
        v = violations[0]
        op = v["violated_operator"]
        desc_map = {
            "latency": "Response exceeded time limit",
            "acknowledgment": "Expected acknowledgment was missing",
            "interruption": "Robot interrupted human speech",
            "repair_exhausted": "Repair retries exhausted",
            "missing_action": "Expected action was missing",
        }
        return desc_map.get(op, f"Violation: {op}")

    return "Contract violation detected"
