"""
Module A: Scenario Loader

Loads all files from a scenario folder into a ScenarioPackage.
Validates folder structure and raises clear errors on missing files.
"""

import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


class LoaderError(Exception):
    """Raised when a required scenario file is missing or malformed."""
    pass


@dataclass
class ScenarioPackage:
    scenario_id: str
    metadata: Dict[str, Any]
    trace: Dict[str, Any]
    contract: Dict[str, Any]
    audit_report: Dict[str, Any]
    counterexample: Optional[Dict[str, Any]] = None
    folder_path: str = ""


REQUIRED_FILES = {
    "traces/trace.json": "trace",
    "contracts/contract.ig.json": "contract",
    "audits/audit_report.json": "audit_report",
    "metadata.yaml": "metadata",
}

OPTIONAL_FILES = {
    "audits/counterexample.json": "counterexample",
}


def load_scenario(scenario_path: str) -> ScenarioPackage:
    """
    Load a complete scenario from a folder path.
    
    Args:
        scenario_path: Path to the scenario folder
        
    Returns:
        ScenarioPackage with all loaded data
        
    Raises:
        LoaderError: If any required file is missing or malformed
    """
    folder = Path(scenario_path)
    
    if not folder.exists():
        raise LoaderError(f"Scenario folder not found: {scenario_path}")
    
    if not folder.is_dir():
        raise LoaderError(f"Not a directory: {scenario_path}")

    scenario_id = folder.name
    loaded = {}

    # Load required files
    for rel_path, key in REQUIRED_FILES.items():
        file_path = folder / rel_path
        if not file_path.exists():
            raise LoaderError(f"Missing required file: {rel_path}")
        
        try:
            if rel_path.endswith(".yaml") or rel_path.endswith(".yml"):
                with open(file_path, "r", encoding="utf-8") as f:
                    loaded[key] = yaml.safe_load(f)
            elif rel_path.endswith(".json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    loaded[key] = json.load(f)
        except json.JSONDecodeError as e:
            raise LoaderError(f"Malformed JSON in {rel_path}: {e}")
        except yaml.YAMLError as e:
            raise LoaderError(f"Malformed YAML in {rel_path}: {e}")

    # Load optional files
    for rel_path, key in OPTIONAL_FILES.items():
        file_path = folder / rel_path
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    loaded[key] = json.load(f)
            except json.JSONDecodeError as e:
                raise LoaderError(f"Malformed JSON in {rel_path}: {e}")
        else:
            loaded[key] = None

    return ScenarioPackage(
        scenario_id=scenario_id,
        metadata=loaded["metadata"],
        trace=loaded["trace"],
        contract=loaded["contract"],
        audit_report=loaded["audit_report"],
        counterexample=loaded.get("counterexample"),
        folder_path=str(folder),
    )


def load_all_scenarios(dataset_root: str) -> List[ScenarioPackage]:
    """
    Load all scenarios from a dataset root directory.
    
    Skips invalid scenarios with a warning instead of crashing.
    """
    root = Path(dataset_root)
    if not root.exists():
        raise LoaderError(f"Dataset root not found: {dataset_root}")

    scenarios = []
    errors = []
    
    for scenario_dir in sorted(root.iterdir()):
        if not scenario_dir.is_dir():
            continue
        try:
            pkg = load_scenario(str(scenario_dir))
            scenarios.append(pkg)
        except LoaderError as e:
            errors.append({"scenario": scenario_dir.name, "error": str(e)})

    return scenarios