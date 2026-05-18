"""
Module H: Batch Runner

Processes all scenario folders under a dataset root.
Generates per-scenario reports and a summary_index.csv.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from modules.loader import load_all_scenarios, LoaderError
from modules.schema_validator import validate_scenario
from modules.evidence_extractor import extract_all_evidence
from modules.report_generator import generate_markdown_report, generate_json_report


def run_batch(
    dataset_root: str,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the full pipeline over all scenarios in a dataset.
    
    Args:
        dataset_root: Path to the dataset directory
        output_dir: Optional output directory for reports (defaults to dataset_root)
        
    Returns:
        Summary dict with results for each scenario
    """
    if output_dir is None:
        output_dir = dataset_root
    
    out_path = Path(output_dir)
    
    # Load all scenarios
    scenarios = load_all_scenarios(dataset_root)
    
    results = []
    errors = []
    
    for scenario in scenarios:
        try:
            # Validate
            validation_errors = validate_scenario(scenario)
            if validation_errors:
                errors.append({
                    "scenario_id": scenario.scenario_id,
                    "errors": validation_errors,
                })
                continue
            
            # Extract evidence
            evidence = extract_all_evidence(scenario.trace, scenario.audit_report)
            
            # Generate reports (no LLM for M2)
            md_report = generate_markdown_report(scenario, evidence)
            json_report = generate_json_report(scenario, evidence)
            
            # Write reports
            report_dir = out_path / scenario.scenario_id / "audits"
            report_dir.mkdir(parents=True, exist_ok=True)
            
            with open(report_dir / "audit_summary.md", "w") as f:
                f.write(md_report)
            
            with open(report_dir / "audit_summary.json", "w") as f:
                json.dump(json_report, f, indent=2, ensure_ascii=False)
            
            results.append({
                "scenario_id": scenario.scenario_id,
                "interaction_type": scenario.metadata.get("interaction_type", ""),
                "contract_id": scenario.audit_report.get("contract_id", ""),
                "verdict": scenario.audit_report["verdict"],
                "num_events": scenario.audit_report.get("num_events", 0),
                "num_violations": scenario.audit_report.get("num_violations", 0),
                "report_path": str(report_dir / "audit_summary.md"),
            })
            
        except Exception as e:
            errors.append({
                "scenario_id": scenario.scenario_id,
                "errors": [str(e)],
            })
    
    # Write summary_index.csv
    if results:
        csv_path = out_path / "summary_index.csv"
        fieldnames = [
            "scenario_id", "interaction_type", "contract_id",
            "verdict", "num_events", "num_violations", "report_path"
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    return {
        "total": len(results) + len(errors),
        "processed": len(results),
        "failed": len(errors),
        "sat_count": sum(1 for r in results if r["verdict"] == "SAT"),
        "unsat_count": sum(1 for r in results if r["verdict"] == "UNSAT"),
        "results": results,
        "errors": errors,
    }
