"""
Module G: Report Generator

Generates Markdown and JSON reports for each scenario.
This module works WITHOUT any LLM — it generates structured reports
from the deterministic audit data only.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime


def generate_markdown_report(
    scenario,
    evidence: Optional[list] = None,
    explanation: Optional[str] = None,
) -> str:
    """
    Generate a Markdown audit summary report.
    
    Args:
        scenario: ScenarioPackage object
        evidence: Optional evidence segments from Module C
        explanation: Optional LLM explanation from Module E
    """
    meta = scenario.metadata
    audit = scenario.audit_report
    trace = scenario.trace
    verdict = audit["verdict"]
    
    lines = []
    lines.append(f"# Scenario Audit Report: {scenario.scenario_id}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().isoformat()}*")
    lines.append("")

    # Scenario Metadata
    lines.append("## Scenario Metadata")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Scenario ID | {scenario.scenario_id} |")
    lines.append(f"| Interaction Type | {meta.get('interaction_type', 'N/A')} |")
    lines.append(f"| Robot Platform | {meta.get('robot_platform', 'N/A')} |")
    lines.append(f"| Source | {meta.get('source_bag', 'synthetic')} |")
    lines.append(f"| Contract | {audit.get('contract_id', 'N/A')} |")
    lines.append("")

    # Contract summary
    lines.append("## Contract")
    lines.append("")
    contract = scenario.contract
    lines.append(f"Contract type: `{contract.get('node', 'unknown')}`")
    lines.append("")

    # Verdict
    lines.append("## Verdict")
    lines.append("")
    if verdict == "SAT":
        lines.append("✅ **SAT** — No contract violation was found.")
    else:
        lines.append(f"❌ **UNSAT** — {audit.get('num_violations', 0)} violation(s) detected.")
    lines.append("")

    # Trace Summary
    lines.append("## Trace Summary")
    lines.append("")
    events = trace.get("events", [])
    lines.append(f"- **Total events**: {len(events)}")
    if events:
        lines.append(f"- **Time span**: {events[0]['timestamp']}s → {events[-1]['timestamp']}s")
        lines.append(f"- **Duration**: {round(events[-1]['timestamp'] - events[0]['timestamp'], 2)}s")
    lines.append("")
    
    # Event table
    lines.append("| # | Time | Agent | Event | Primitive | Object |")
    lines.append("|---|------|-------|-------|-----------|--------|")
    for evt in events:
        obj = evt.get("object") or "—"
        lines.append(
            f"| {evt['event_id']} | {evt['timestamp']}s | {evt['agent']} | "
            f"{evt['event_type']} | {evt['primitive']} | {obj} |"
        )
    lines.append("")

    # Violation Summary
    if verdict == "UNSAT":
        lines.append("## Violation Summary")
        lines.append("")
        for v in audit.get("violations", []):
            lines.append(f"### {v['violation_id']}: {v['violated_operator']}")
            lines.append("")
            lines.append(f"| Field | Value |")
            lines.append(f"|-------|-------|")
            lines.append(f"| Operator | {v['violated_operator']} |")
            lines.append(f"| Site | {v.get('site', 'N/A')} |")
            lines.append(f"| Trigger Event | {v.get('trigger_event_id', 'N/A')} |")
            lines.append(f"| Trigger Time | {v.get('trigger_time', 'N/A')}s |")
            lines.append(f"| Expected | {v.get('expected_event', 'N/A')} |")
            lines.append(f"| Observed | {v.get('observed_event', 'N/A')} |")
            lines.append(f"| Deadline | {v.get('deadline_seconds', 'N/A')}s |")
            lines.append(f"| Falsification | {v.get('falsification_time', 'N/A')}s |")
            lines.append(f"| Attribution | {v['agent_attribution']} |")
            lines.append(f"| Error Code | {v.get('error_code', 'N/A')} |")
            lines.append("")

        # Counterexample
        if scenario.counterexample:
            lines.append("## Counterexample")
            lines.append("")
            cx = scenario.counterexample
            lines.append(f"**Violated obligation**: {cx.get('violated_obligation', 'N/A')}")
            lines.append("")
            lines.append(f"- **Trigger**: {cx['trigger'].get('description', 'N/A')}")
            lines.append(f"- **Expected**: {cx['expected'].get('event', 'N/A')} in {cx['expected'].get('time_window', 'N/A')}")
            lines.append(f"- **Observed**: {cx['observed'].get('description', 'N/A')}")
            lines.append(f"- **Falsification**: {cx['falsification'].get('description', 'N/A')}")
            lines.append(f"- **Attribution**: {cx.get('attribution', 'N/A')}")
            lines.append("")

    # LLM Explanation
    if explanation:
        lines.append("## Human-Readable Explanation")
        lines.append("")
        lines.append(explanation)
        lines.append("")

    # Files Used
    lines.append("## Files Used")
    lines.append("")
    lines.append(f"- `traces/trace.json`")
    lines.append(f"- `contracts/contract.ig.json`")
    lines.append(f"- `audits/audit_report.json`")
    if scenario.counterexample:
        lines.append(f"- `audits/counterexample.json`")
    lines.append(f"- `metadata.yaml`")
    lines.append("")

    return "\n".join(lines)


def generate_json_report(
    scenario,
    evidence: Optional[list] = None,
    explanation: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a JSON audit summary report."""
    return {
        "scenario_id": scenario.scenario_id,
        "metadata": scenario.metadata,
        "contract_id": scenario.audit_report.get("contract_id"),
        "verdict": scenario.audit_report["verdict"],
        "num_events": scenario.audit_report.get("num_events", 0),
        "num_violations": scenario.audit_report.get("num_violations", 0),
        "violations": scenario.audit_report.get("violations", []),
        "counterexample": scenario.counterexample,
        "explanation": explanation,
        "generated_at": datetime.now().isoformat(),
    }
