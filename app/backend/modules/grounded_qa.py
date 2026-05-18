"""
Module F: Grounded Q&A

Handles the core Q&A logic: safety filtering, prompt building,
LLM call orchestration, and fallback templates.
Separated from the router so it can be tested independently.
"""

import logging
from typing import Dict, Any, Optional

from llm.provider import LLMProvider
from modules.prompt_builder import build_qa_prompt

logger = logging.getLogger(__name__)

# Mental-state keywords the LLM must not reason about
_UNSUPPORTED_KEYWORDS = [
    "confused", "frustrated", "angry", "happy", "scared",
    "attention", "intention", "feeling", "emotion",
    "thinking", "wanted to", "tried to", "meant to",
    "mood", "distracted", "bored", "interested",
]


def check_unsupported(question: str) -> Optional[str]:
    """
    Check if a question asks about unsupported information
    (mental states, emotions, intent).
    Returns a refusal string, or None if the question is allowed.
    """
    q = question.lower()
    for kw in _UNSUPPORTED_KEYWORDS:
        if kw in q:
            return (
                "The audit package does not contain evidence about the "
                f"human's mental state or {kw}. The auditor only tracks "
                "observable interaction events (speech, gesture, timing). "
                "No inference about intent, emotion, or cognition is supported."
            )
    return None


def answer_question(
    llm: LLMProvider,
    question: str,
    scenario,
) -> Dict[str, Any]:
    """
    Answer a grounded question about a scenario.
    
    1. Safety filter (mental-state keywords)
    2. Build prompt from audit package
    3. Call LLM
    4. Fallback to templates on error
    
    Returns dict with answer, source, grounded flag.
    """
    # 1. Safety filter
    refusal = check_unsupported(question)
    if refusal:
        return {
            "answer": refusal,
            "source": "safety_filter",
            "grounded": True,
        }

    # 2. Build prompt
    system_prompt, user_prompt = build_qa_prompt(
        question=question,
        scenario_id=scenario.scenario_id,
        metadata=scenario.metadata,
        audit_report=scenario.audit_report,
        counterexample=scenario.counterexample,
        trace_events=scenario.trace.get("events", []),
    )

    # 3. Call LLM
    try:
        answer = llm.generate(system_prompt, user_prompt)
        return {
            "answer": answer,
            "source": llm.name(),
            "grounded": True,
        }
    except Exception as e:
        logger.error(f"LLM Q&A failed: {e}")
        # 4. Fallback
        answer = template_answer(question, scenario)
        return {
            "answer": answer,
            "source": "template_fallback",
            "grounded": True,
        }


def template_answer(question: str, scenario) -> str:
    """Deterministic template answers when LLM is unavailable."""
    q = question.lower().strip().rstrip("?")
    audit = scenario.audit_report
    verdict = audit["verdict"]
    violations = audit.get("violations", [])

    # Check "when/decidable" BEFORE "fail" — "failure" contains "fail"
    if any(k in q for k in ["decidable", "falsification", "when did"]):
        if verdict == "SAT":
            return "No failure occurred — the interaction satisfied all contract obligations."
        v = violations[0] if violations else {}
        return f"The failure became decidable at {v.get('falsification_time', 'N/A')}s."

    if any(k in q for k in ["why", "fail", "what happened"]):
        if verdict == "SAT":
            return "This scenario passed — no contract violation was detected."
        v = violations[0] if violations else {}
        return (
            f"The interaction failed due to a {v.get('violated_operator', 'unknown')} violation. "
            f"The failure was triggered at {v.get('trigger_time', 'N/A')}s "
            f"and attributed to {v.get('agent_attribution', 'unknown')}."
        )

    if any(k in q for k in ["expected", "what was expected"]):
        v = violations[0] if violations else {}
        return f"The expected event was '{v.get('expected_event', 'N/A')}' within {v.get('deadline_seconds', 'N/A')}s of the trigger."

    if any(k in q for k in ["missing", "observed"]):
        v = violations[0] if violations else {}
        obs = v.get("observed_event")
        return f"The observed event was '{obs}'." if obs else "No matching event was observed before the deadline."

    if any(k in q for k in ["trigger", "which event triggered"]):
        v = violations[0] if violations else {}
        return f"The obligation was triggered by event {v.get('trigger_event_id', 'N/A')} at {v.get('trigger_time', 'N/A')}s."

    if any(k in q for k in ["agent", "attributed", "blame", "who"]):
        v = violations[0] if violations else {}
        return f"The failure is attributed to {v.get('agent_attribution', 'unknown')}."

    if any(k in q for k in ["contract", "operator", "which part", "violated"]):
        v = violations[0] if violations else {}
        return f"The violated contract operator is '{v.get('violated_operator', 'N/A')}' at clause path {v.get('clause_path', 'N/A')}."

    if any(k in q for k in ["counterexample", "show"]):
        if scenario.counterexample:
            cx = scenario.counterexample
            return f"Counterexample: {cx.get('violated_obligation', 'N/A')}. Trigger at {cx['trigger']['time']}s, falsified at {cx['falsification']['time']}s."
        return "No counterexample available (scenario passed)."

    if any(k in q for k in ["summarize", "summary", "overview"]):
        return (
            f"Scenario '{scenario.scenario_id}' resulted in {verdict}. "
            f"The trace contained {audit.get('num_events', 0)} events with "
            f"{audit.get('num_violations', 0)} violation(s)."
        )

    return "This information is not present in the loaded audit package."
