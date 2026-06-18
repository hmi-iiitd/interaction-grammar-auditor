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
from src.audit.auditor import Auditor

DATASET_NAO_DIR = ROOT_DIR / "dataset_nao"
MATRIX_FILE = DATASET_NAO_DIR / "scenario_matrix.json"

def run_reproducibility_test():
    if not MATRIX_FILE.exists():
        print("Error: scenario_matrix.json not found.")
        return

    with open(MATRIX_FILE, "r") as f:
        matrix = json.load(f)

    scenarios = [s["scenario_id"] for s in matrix]
    repro_results = []

    print(f"Running reproducibility checks (3x) for {len(scenarios)} scenarios...\n")
    print(f"{'Scenario':<30} | {'Run 1':<10} | {'Run 2':<10} | {'Run 3':<10} | {'Status'}")
    print("-" * 75)

    for sid in scenarios:
        scenario_dir = DATASET_NAO_DIR / sid
        contract_path = scenario_dir / "contract.ig.json"
        trace_path = scenario_dir / "trace.jsonl"

        if not contract_path.exists() or not trace_path.exists():
            print(f"{sid:<30} | Missing files")
            continue

        run_verdicts = []
        try:
            # We load the contract and trace once, but run the audit multiple times
            with open(contract_path, 'r', encoding='utf-8-sig') as f:
                c_data = json.load(f)
            prepare_contract_for_validation(c_data)
            ast = ContractParser().parse(c_data)
            trace = Trace.from_file(str(trace_path))

            for i in range(3):
                res = Auditor(ast).audit(trace)
                run_verdicts.append(res.verdict)
        except Exception as e:
            print(f"{sid:<30} | ❌ Error: {e}")
            continue

        is_deterministic = all(v == run_verdicts[0] for v in run_verdicts)
        status = "OK" if is_deterministic else "FAILED"

        print(f"{sid:<30} | {run_verdicts[0]:<10} | {run_verdicts[1]:<10} | {run_verdicts[2]:<10} | {status}")

        repro_results.append({
            "scenario_id": sid,
            "runs": run_verdicts,
            "deterministic": is_deterministic
        })

    # Save reproducibility table
    md_table = "| Scenario | Run 1 | Run 2 | Run 3 | Result |\n"
    md_table += "| :--- | :---: | :---: | :---: | :---: |\n"
    for row in repro_results:
        v = row["runs"]
        status = "YES" if row["deterministic"] else "NO"
        md_table += f"| {row['scenario_id']} | {v[0]} | {v[1]} | {v[2]} | {status} |\n"

    with open(DATASET_NAO_DIR / "reproducibility_report.md", "w") as f:
        f.write("# Reproducibility Report\n\n")
        f.write("The following table shows the consistency of audit verdicts across three independent runs.\n\n")
        f.write(md_table)

    print("\nReproducibility check complete. Report saved to dataset_nao/reproducibility_report.md")

if __name__ == "__main__":
    run_reproducibility_test()
