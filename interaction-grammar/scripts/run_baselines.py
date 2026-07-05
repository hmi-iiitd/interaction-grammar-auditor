import json
from pathlib import Path
from typing import Dict, Any, List
from baseline_monitors import TaskOutcomeMonitor, RuleBasedMonitor, FSMMonitor, SCENARIO_MATRIX

def load_trace(scenario_id: str) -> List[Dict]:
    trace_path = Path(f"interaction-grammar/dataset_nao/{scenario_id}/trace.jsonl")
    if not trace_path.exists():
        print(f"Warning: Trace not found for {scenario_id}")
        return []

    trace = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            trace.append(json.loads(line))
    return trace

def run_baselines():
    monitors = {
        "Task Outcome": TaskOutcomeMonitor(),
        "Rule Monitor": RuleBasedMonitor(),
        "FSM Monitor": FSMMonitor()
    }

    results = []

    # We need the Auditor results too to match the table.
    # The Auditor results are in report.json for each scenario.

    for scenario in SCENARIO_MATRIX:
        sid = scenario["id"]
        trace = load_trace(sid)

        # Get Auditor verdict from report.json
        auditor_verdict = "UNKNOWN"
        report_path = Path(f"interaction-grammar/dataset_nao/{sid}/report.json")
        if report_path.exists():
            with open(report_path, "r") as f:
                report = json.load(f)
                auditor_verdict = report.get("verdict", "UNKNOWN")

        # Normalizing Auditor verdict to PASS/FAIL for the table
        auditor_display = "PASS" if auditor_verdict in ["PASS", "SAT"] else "FAIL"

        scenario_results = {
            "Scenario": sid,
            "Auditor": auditor_display,
        }

        for name, monitor in monitors.items():
            res = monitor.audit(sid, trace)
            scenario_results[name] = res["verdict"]

        results.append(scenario_results)
        print(f"Processed {sid}: Auditor={auditor_display}, TaskOutcome={scenario_results['Task Outcome']}, Rule={scenario_results['Rule Monitor']}, FSM={scenario_results['FSM Monitor']}")

    # Generate Markdown Table
    header = "| Scenario | Auditor | Task Outcome | Rule Monitor | FSM Monitor |"
    separator = "| :--- | :---: | :---: | :---: | :---: |"
    rows = []
    for r in results:
        row = f"| {r['Scenario']} | {r['Auditor']} | {r['Task Outcome']} | {r['Rule Monitor']} | {r['FSM Monitor']} |"
        rows.append(row)

    table = "\n".join([header, separator] + rows)

    with open("interaction-grammar/dataset_nao/baseline_comparison.md", "w") as f:
        f.write(table)

    print("\nSuccessfully updated interaction-grammar/dataset_nao/baseline_comparison.md")

if __name__ == "__main__":
    run_baselines()
