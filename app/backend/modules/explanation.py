"""
Module E: LLM Explanation Generator

Generates human-readable explanations of audit results using the LLM.
Falls back to templates if LLM is unavailable.
"""

import logging
from typing import Dict, Any, Optional

from llm.provider import LLMProvider
from modules.prompt_builder import build_explanation_prompt

logger = logging.getLogger(__name__)


def generate_explanation(
    llm: LLMProvider,
    scenario_id: str,
    metadata: Dict[str, Any],
    audit_report: Dict[str, Any],
    trace_events: list,
) -> str:
    """
    Generate a human-readable explanation for an audit result.
    
    Uses the LLM provider via the prompt builder.
    """
    verdict = audit_report["verdict"]
    violations = audit_report.get("violations", [])

    if verdict == "SAT":
        return (
            f"Scenario '{scenario_id}' passed the audit. "
            f"All contract obligations were satisfied. "
            f"The trace contained {audit_report.get('num_events', 0)} events "
            f"with no violations detected."
        )

    violation = violations[0] if violations else None

    # Build evidence events from trace
    evidence_events = trace_events
    if violation and violation.get("trigger_time") is not None:
        t_start = max(0, violation["trigger_time"] - 1.0)
        t_end = (violation.get("falsification_time") or violation["trigger_time"] + 5.0) + 1.0
        evidence_events = [e for e in trace_events if t_start <= e["timestamp"] <= t_end]
        if not evidence_events:
            evidence_events = trace_events  # fallback to full trace

    system_prompt, user_prompt = build_explanation_prompt(
        scenario_id, metadata, verdict, violation, evidence_events
    )

    try:
        explanation = llm.generate(system_prompt, user_prompt)
        logger.info(f"LLM explanation generated: {len(explanation)} chars via {llm.name()}")
        return explanation
    except Exception as e:
        logger.error(f"LLM explanation failed: {e}")
        # Fallback to template
        return _template_explanation(scenario_id, verdict, violation)


def _template_explanation(
    scenario_id: str,
    verdict: str,
    violation: Optional[Dict[str, Any]],
) -> str:
    """Fallback template explanation when LLM is unavailable."""
    if not violation:
        return f"Scenario '{scenario_id}' failed the audit but no violation details are available."

    parts = []
    parts.append(
        f"The interaction violated the {violation.get('violated_operator', 'unknown')} "
        f"requirement at the {violation.get('site', 'unknown')} site."
    )

    if violation.get("trigger_event_id") and violation.get("trigger_time") is not None:
        parts.append(
            f"The obligation was triggered by event {violation['trigger_event_id']} "
            f"at {violation['trigger_time']}s."
        )

    if violation.get("expected_event"):
        deadline = violation.get("deadline_seconds")
        if deadline:
            parts.append(
                f"The contract expected '{violation['expected_event']}' "
                f"within {deadline}s of the trigger."
            )
        else:
            parts.append(f"The contract expected '{violation['expected_event']}'.")

    if violation.get("observed_event"):
        parts.append(f"The observed event was '{violation['observed_event']}'.")
    else:
        parts.append(
            f"No matching event was observed before the deadline."
        )

    if violation.get("falsification_time") is not None:
        parts.append(
            f"The violation became decidable at {violation['falsification_time']}s."
        )

    if violation.get("agent_attribution"):
        parts.append(f"The failure is attributed to {violation['agent_attribution']}.")

    return " ".join(parts) + " [template fallback — LLM unavailable]"
