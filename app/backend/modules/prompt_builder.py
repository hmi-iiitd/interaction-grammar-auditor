"""
Module D: Prompt Builder

Builds constrained prompts for the LLM using only structured data.
The prompt must include:
- System instruction: do not infer beyond data
- Scenario metadata
- Audit verdict
- Violation object
- Evidence trace segment
- Allowed answer format
"""

from typing import Dict, Any, Optional


SYSTEM_INSTRUCTION = """You are a precise scientific assistant that explains Human-Robot Interaction audit results.

STRICT RULES:
1. You MUST only use information present in the provided structured data.
2. You MUST NOT infer intent, emotion, cause, or mental state unless explicitly present in the data.
3. You MUST NOT invent events, timestamps, or agents not present in the trace.
4. You MUST NOT change the SAT/UNSAT verdict.
5. If asked about something not in the data, say: "This information is not present in the loaded audit package."
6. Keep explanations factual, concise, and grounded in the audit data.
7. Reference specific event IDs, timestamps, and agent names from the data.
"""


def build_explanation_prompt(
    scenario_id: str,
    metadata: Dict[str, Any],
    verdict: str,
    violation: Optional[Dict[str, Any]],
    evidence_events: list,
) -> tuple[str, str]:
    """
    Build system + user prompts for the explanation generator (Module E).
    
    Returns:
        (system_prompt, user_prompt) tuple
    """
    user_parts = []

    user_parts.append(f"## Scenario: {scenario_id}")
    user_parts.append(f"Interaction type: {metadata.get('interaction_type', 'N/A')}")
    user_parts.append(f"Robot platform: {metadata.get('robot_platform', 'N/A')}")
    user_parts.append(f"Verdict: {verdict}")
    user_parts.append("")

    if violation:
        user_parts.append("## Violation Details")
        user_parts.append(f"- Violation ID: {violation.get('violation_id')}")
        user_parts.append(f"- Violated operator: {violation.get('violated_operator')}")
        user_parts.append(f"- Site: {violation.get('site')}")
        user_parts.append(f"- Trigger event: {violation.get('trigger_event_id')} at {violation.get('trigger_time')}s")
        user_parts.append(f"- Expected event: {violation.get('expected_event')}")
        user_parts.append(f"- Observed event: {violation.get('observed_event') or 'MISSING (not observed)'}")
        user_parts.append(f"- Deadline: {violation.get('deadline_seconds')}s")
        user_parts.append(f"- Falsification time: {violation.get('falsification_time')}s")
        user_parts.append(f"- Agent attribution: {violation.get('agent_attribution')}")
        user_parts.append(f"- Error code: {violation.get('error_code')}")
        user_parts.append("")

    if evidence_events:
        user_parts.append("## Evidence Trace Segment")
        for evt in evidence_events:
            obj = evt.get('object') or ''
            user_parts.append(
                f"  [{evt['event_id']}] {evt['timestamp']}s | {evt['agent']} | "
                f"{evt['event_type']} | {evt['primitive']}"
                f"{f' | {obj}' if obj else ''}"
            )
        user_parts.append("")

    user_parts.append("## Task")
    user_parts.append(
        "Generate a clear, factual, human-readable explanation of this audit result. "
        "The explanation MUST include: (1) what failed, (2) when the obligation was triggered, "
        "(3) what was expected, (4) what was observed or missing, "
        "(5) when the violation became decidable, (6) the failure site, "
        "(7) agent attribution. "
        "Do NOT infer intent, emotion, or cause beyond what is in the data."
    )

    return SYSTEM_INSTRUCTION, "\n".join(user_parts)


def build_qa_prompt(
    question: str,
    scenario_id: str,
    metadata: Dict[str, Any],
    audit_report: Dict[str, Any],
    counterexample: Optional[Dict[str, Any]],
    trace_events: list,
) -> tuple[str, str]:
    """
    Build system + user prompts for grounded Q&A (Module F).
    
    Returns:
        (system_prompt, user_prompt) tuple
    """
    user_parts = []

    user_parts.append(f"## Loaded Audit Package: {scenario_id}")
    user_parts.append(f"Verdict: {audit_report['verdict']}")
    user_parts.append(f"Contract: {audit_report.get('contract_id', 'N/A')}")
    user_parts.append(f"Events: {audit_report.get('num_events', 0)}")
    user_parts.append(f"Violations: {audit_report.get('num_violations', 0)}")
    user_parts.append("")

    violations = audit_report.get("violations", [])
    if violations:
        user_parts.append("## Violations")
        for v in violations:
            user_parts.append(f"- {v['violation_id']}: {v['violated_operator']}")
            user_parts.append(f"  Trigger: {v.get('trigger_event_id')} at {v.get('trigger_time')}s")
            user_parts.append(f"  Expected: {v.get('expected_event')}")
            user_parts.append(f"  Observed: {v.get('observed_event') or 'MISSING'}")
            user_parts.append(f"  Deadline: {v.get('deadline_seconds')}s")
            user_parts.append(f"  Falsification: {v.get('falsification_time')}s")
            user_parts.append(f"  Attribution: {v.get('agent_attribution')}")
        user_parts.append("")

    if counterexample:
        user_parts.append("## Counterexample")
        user_parts.append(f"Obligation: {counterexample.get('violated_obligation')}")
        user_parts.append(f"Trigger: {counterexample['trigger']['event_id']} at {counterexample['trigger']['time']}s")
        user_parts.append(f"Expected: {counterexample['expected']['event']} in {counterexample['expected']['time_window']}")
        user_parts.append(f"Observed: {counterexample['observed']['description']}")
        user_parts.append(f"Falsification: {counterexample['falsification']['time']}s")
        user_parts.append("")

    # Include trace (abbreviated if long)
    user_parts.append("## Trace Events")
    display_events = trace_events[:20]  # cap at 20
    for evt in display_events:
        obj = evt.get('object') or ''
        user_parts.append(
            f"  [{evt['event_id']}] {evt['timestamp']}s | {evt['agent']} | "
            f"{evt['event_type']} | {evt['primitive']}"
            f"{f' | {obj}' if obj else ''}"
        )
    if len(trace_events) > 20:
        user_parts.append(f"  ... ({len(trace_events) - 20} more events)")
    user_parts.append("")

    user_parts.append(f"## User Question")
    user_parts.append(question)
    user_parts.append("")
    user_parts.append(
        "Answer the question using ONLY the data above. "
        "Reference specific event IDs and timestamps. "
        "If the answer is not available from the data, say: "
        "'This information is not present in the loaded audit package.'"
    )

    return SYSTEM_INSTRUCTION, "\n".join(user_parts)
