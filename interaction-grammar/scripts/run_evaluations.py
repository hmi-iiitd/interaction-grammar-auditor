import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure src is in path
import os
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.compiler.parser import ContractParser
from src.compiler.validator import prepare_contract_for_validation
from src.audit.trace import Trace
from src.audit.auditor import Auditor, AuditVerdict

# Import our new baseline monitors
from baseline_monitors import TaskOutcomeMonitor, RuleBasedMonitor, FSMMonitor

DATASET_NAO_DIR = ROOT_DIR / "dataset_nao"
MATRIX_FILE = DATASET_NAO_DIR / "scenario_matrix.json"

def run_full_eval():
    if not MATRIX_FILE.exists():
        print("Error: scenario_matrix.json not found.")
        return

    with open(MATRIX_FILE, "r") as f:
        matrix = json.load(f)

    scenarios = [s["scenario_id"] for s in matrix]

    # Initialize monitors
    outcome_mon = TaskOutcomeMonitor()
    rule_mon = RuleBasedMonitor()
    fsm_mon = FSMMonitor()

    results_table = []

    print(f"Running evaluation on {len(scenarios)} scenarios...\n")
    print(f"{'Scenario':<30} | {'Auditor':<10} | {'Outcome':<10} | {'Rules':<10} | {'FSM':<10}")
    print("-" * 75)

    for sid in scenarios:
        scenario_dir = DATASET_NAO_DIR / sid
        contract_path = scenario_dir / "contract.ig.json"
        trace_path = scenario_dir / "trace.jsonl"

        if not contract_path.exists() or not trace_path.exists():
            print(f"{sid:<30} | Missing files")
            continue

        # 1. Actual Auditor Result
        try:
            with open(contract_path, 'r', encoding='utf-8-sig') as f:
                c_data = json.load(f)
            prepare_contract_for_validation(c_data)
            ast = ContractParser().parse(c_data)
            trace = Trace.from_file(str(trace_path))
            auditor_res = Auditor(ast).audit(trace)
            auditor_verdict = auditor_res.verdict
        except Exception as e:
            auditor_verdict = "ERR"

        # 2. Baselines
        # Load raw trace for baselines
        raw_events = []
        with open(trace_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                if line.strip(): raw_events.append(json.loads(line))

        outcome_v = outcome_mon.audit(sid, raw_events)["verdict"]
        rule_v = rule_mon.audit(sid, raw_events)["verdict"]
        fsm_v = fsm_mon.audit(sid, raw_events)["verdict"]

        print(f"{sid:<30} | {auditor_verdict:<10} | {outcome_v:<10} | {rule_v:<10} | {fsm_v:<10}")

        results_table.append({
            "scenario_id": sid,
            "auditor": auditor_verdict,
            "outcome": outcome_v,
            "rules": rule_v,
            "fsm": fsm_v
        })

    # Generate the final Markdown Table
    md_table = "| Scenario | Auditor | Task Outcome | Rule Monitor | FSM Monitor |\n"
    md_table += "| :--- | :---: | :---: | :---: | :---: |\n"
    for row in results_table:
        md_table += f"| {row['scenario_id']} | {row['auditor']} | {row['outcome']} | {row['rules']} | {row['fsm']} |\n"

    with open(DATASET_NAO_DIR / "baseline_comparison.md", "w") as f:
        f.write(md_table)

    print("\nEvaluation complete. Table saved to dataset_nao/baseline_comparison.md")

if __name__ == "__main__":
    run_full_eval()
