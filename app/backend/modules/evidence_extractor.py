"""
Module C: Evidence Extractor

For each violation, extracts the relevant trace segment:
- Trigger event
- Events between trigger_time and falsification_time
- Expected event
- Observed/missing event
- Neighboring events before/after for context
"""

from typing import Dict, Any, Optional, List


def extract_evidence(
    trace: Dict[str, Any],
    violation: Dict[str, Any],
    context_margin: float = 1.5,
) -> Dict[str, Any]:
    """
    Extract the evidence segment for a single violation.
    
    Args:
        trace: The transformed trace.json data
        violation: A single violation from audit_report.json
        context_margin: Seconds of context to include before/after the window
        
    Returns:
        Evidence segment dict with trigger, window events, expected/observed
    """
    events = trace.get("events", [])
    trigger_time = violation.get("trigger_time", 0) or 0
    falsification_time = violation.get("falsification_time") or (trigger_time + 5.0)
    trigger_event_id = violation.get("trigger_event_id")

    # Evidence window with context margin
    window_start = max(0, trigger_time - context_margin)
    window_end = falsification_time + context_margin

    # Find trigger event
    trigger_event = None
    for evt in events:
        if evt["event_id"] == trigger_event_id:
            trigger_event = evt
            break

    # Collect events in the window
    window_events = []
    for evt in events:
        if window_start <= evt["timestamp"] <= window_end:
            window_events.append(evt)

    # Determine expected and observed
    expected = {
        "event": violation.get("expected_event"),
        "deadline": violation.get("deadline_seconds"),
    }
    
    observed = {
        "event": violation.get("observed_event"),
        "found": violation.get("observed_event") is not None,
    }

    return {
        "trigger_event": trigger_event,
        "trigger_time": trigger_time,
        "falsification_time": falsification_time,
        "window_start": round(window_start, 2),
        "window_end": round(window_end, 2),
        "window_duration": round(window_end - window_start, 2),
        "window_events": window_events,
        "expected": expected,
        "observed": observed,
        "neighboring_before": [e for e in events if trigger_time - context_margin <= e["timestamp"] < trigger_time],
        "neighboring_after": [e for e in events if falsification_time < e["timestamp"] <= falsification_time + context_margin],
    }


def extract_all_evidence(
    trace: Dict[str, Any],
    audit_report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract evidence segments for all violations in an audit report.
    """
    violations = audit_report.get("violations", [])
    return [extract_evidence(trace, v) for v in violations]
