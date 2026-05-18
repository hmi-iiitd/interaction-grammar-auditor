"""
Audit Mapper — Transforms existing AuditResult.to_dict() output into the PDF-expected
audit_report and counterexample schemas WITHOUT modifying the auditor internals.

This is a pure mapping layer that:
1. Converts PASS/FAIL → SAT/UNSAT
2. Enriches violations with trigger_event_id, falsification_time, etc.
3. Generates counterexample objects from witness data
4. Relativizes timestamps (subtracts first event time)
5. Auto-generates event_ids (e001, e002, ...)
"""

import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class TransformedEvent:
    event_id: str
    timestamp: float
    agent: str
    event_type: str
    primitive: str
    modality: str
    object: Optional[str] = None
    source_topic: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class TransformedViolation:
    violation_id: str
    violated_operator: str
    agent_attribution: str
    site: Optional[str] = None
    trigger_event_id: Optional[str] = None
    expected_event: Optional[str] = None
    observed_event: Optional[str] = None
    deadline_seconds: Optional[float] = None
    trigger_time: Optional[float] = None
    falsification_time: Optional[float] = None
    error_code: Optional[str] = None
    clause_path: Optional[str] = None


@dataclass
class TransformedAuditReport:
    scenario_id: str
    contract_id: str
    verdict: str
    num_events: int = 0
    num_violations: int = 0
    violations: List[Dict] = field(default_factory=list)
    raw_auditor_output: Optional[Dict] = None


@dataclass
class TransformedCounterexample:
    scenario_id: str
    violation_id: str
    violated_obligation: str
    trigger: Dict = field(default_factory=dict)
    expected: Dict = field(default_factory=dict)
    observed: Dict = field(default_factory=dict)
    falsification: Dict = field(default_factory=dict)
    attribution: str = ""
    site: Optional[str] = None
    evidence_window: Optional[Dict] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prim_to_event_type(prim: str, obj: Optional[str] = None) -> str:
    """Convert IG primitive + object to a human-readable event type."""
    base_map = {"σ": "speaking_start", "ρ": "speaking_end", "τ": "point", "α": "action"}
    base = base_map.get(prim, prim)
    if obj:
        return obj  # e.g. "prompt", "ack", "confirm", "interrupt"
    return base


def _agent_to_topic(agent: str) -> str:
    """Map agent to likely ROS topic."""
    if "robot" in agent:
        return "/interaction/robot_event"
    elif "human" in agent:
        return "/interaction/human_event"
    return "/interaction/event"


def _parse_budget_seconds(budget_str: Optional[str]) -> Optional[float]:
    """Parse a budget string like '≤8.0s' or '≤1.0s' into seconds."""
    if not budget_str:
        return None
    clean = budget_str.replace("≤", "").replace("<=", "").strip()
    match = re.match(r'^([\d.]+)\s*(s|ms|m)?$', clean)
    if match:
        val = float(match.group(1))
        unit = match.group(2)
        if unit == "ms":
            return val / 1000.0
        elif unit == "m":
            return val * 60.0
        return val  # seconds
    return None


def _error_code_to_operator(error_code: str, operator: str) -> str:
    """Map auditor error_code + operator to a human-readable violated_operator."""
    mapping = {
        "V_SEQ_LATENCY_EXCEEDED": "latency",
        "V_SEQ_MISSING_RIGHT": "acknowledgment",
        "V_PAR_SYNC_START": "synchronization",
        "V_PAR_MISSING_LEFT": "parallel_missing",
        "V_PAR_MISSING_RIGHT": "parallel_missing",
        "V_NEG_VIOLATED": "interruption",
        "V_REPAIR_EXHAUSTED": "repair_exhausted",
        "V_BIND_LATENCY_EXCEEDED": "bind_latency",
        "V_ACT_MISSING": "missing_action",
    }
    return mapping.get(error_code, operator)


def _clause_path_to_site(clause_path: str, error_code: str) -> str:
    """Derive a failure site from the clause path."""
    if "NEG" in (error_code or ""):
        return "interruption_guard"
    if "MISSING" in (error_code or ""):
        return "closure"
    if "LATENCY" in (error_code or ""):
        return "timing"
    if "REPAIR" in (error_code or ""):
        return "repair"
    if "SYNC" in (error_code or ""):
        return "synchronization"
    # Fallback: use last segment of clause_path
    return clause_path.split(".")[-1] if clause_path else "unknown"


# ---------------------------------------------------------------------------
# Trace Transformer
# ---------------------------------------------------------------------------

def transform_trace(raw_events: List[Dict], t0: Optional[float] = None) -> Dict:
    """
    Transform raw JSONL trace events into the PDF-expected trace.json format.
    
    - Adds event_id fields (e001, e002, ...)
    - Relativizes timestamps
    - Adds event_type, modality, source_topic fields
    """
    # Sort by timestamp
    sorted_events = sorted(raw_events, key=lambda e: e["t"])

    if t0 is None and sorted_events:
        t0 = sorted_events[0]["t"]
    elif t0 is None:
        t0 = 0.0

    transformed = []
    for i, evt in enumerate(sorted_events):
        te = TransformedEvent(
            event_id=f"e{i+1:03d}",
            timestamp=round(evt["t"] - t0, 2),
            agent=evt["agent"],
            event_type=_prim_to_event_type(evt["prim"], evt.get("object")),
            primitive=evt["prim"],
            modality=evt.get("channel", "speech"),
            object=evt.get("object"),
            source_topic=_agent_to_topic(evt["agent"]),
            confidence=None,
        )
        transformed.append(asdict(te))

    return {"events": transformed}


# ---------------------------------------------------------------------------
# Audit Report Transformer
# ---------------------------------------------------------------------------

def transform_audit_report(
    raw_audit: Dict,
    scenario_id: str,
    contract_id: str,
    trace_events: List[Dict],
    t0: float = 0.0,
) -> Dict:
    """
    Transform AuditResult.to_dict() into the PDF-expected audit_report.json format.
    """
    verdict = "SAT" if raw_audit.get("verdict") == "PASS" else "UNSAT"

    violations = []
    if verdict == "UNSAT":
        v = _extract_violation(raw_audit, trace_events, t0, violation_idx=1)
        violations.append(asdict(v))

    report = TransformedAuditReport(
        scenario_id=scenario_id,
        contract_id=contract_id,
        verdict=verdict,
        num_events=len(trace_events),
        num_violations=len(violations),
        violations=violations,
        raw_auditor_output=raw_audit,
    )
    return asdict(report)


def _find_witness_events(witness: Dict) -> Dict:
    """Recursively find event data from various witness shapes."""
    result = {"trigger": None, "end": None, "all_indices": []}
    
    # Direct event shape: {"idx": N, "event": {...}}
    if "idx" in witness and "event" in witness:
        evt = witness["event"]
        idx = witness["idx"]
        result["all_indices"].append(idx)
        if result["trigger"] is None:
            result["trigger"] = {"idx": idx, "event": evt}
        result["end"] = {"idx": idx, "event": evt}
        return result

    # left_event / right_event shape (sequence violations)
    if "left_event" in witness:
        le = witness["left_event"]
        if "idx" in le:
            result["trigger"] = le
            result["all_indices"].append(le["idx"])
    if "right_event" in witness:
        re = witness["right_event"]
        if "idx" in re:
            result["end"] = re
            result["all_indices"].append(re["idx"])

    # left / right shape (negation, nested)
    for key in ["left", "right"]:
        if key in witness and isinstance(witness[key], dict):
            sub = _find_witness_events(witness[key])
            if sub["trigger"] and result["trigger"] is None:
                result["trigger"] = sub["trigger"]
            if sub["end"]:
                result["end"] = sub["end"]
            result["all_indices"].extend(sub["all_indices"])

    return result


def _extract_violation(
    raw: Dict, trace_events: List[Dict], t0: float, violation_idx: int
) -> TransformedViolation:
    """Extract a single violation from the raw auditor output."""
    error_code = raw.get("error_code", "")
    operator = raw.get("operator", "")
    clause_path = raw.get("clause_path", "$")
    budget_str = raw.get("budget")
    responsible = raw.get("responsible_agent") or "unknown"
    witness = raw.get("witness", {})

    # Extract events from any witness shape
    w_events = _find_witness_events(witness)
    
    trigger_event_id = None
    trigger_time = None
    if w_events["trigger"]:
        t_data = w_events["trigger"]
        idx = t_data.get("idx")
        evt = t_data.get("event", {})
        if idx is not None:
            trigger_event_id = f"e{idx + 1:03d}"
        if evt and "t" in evt:
            trigger_time = round(evt["t"] - t0, 2)

    # Calculate falsification time
    deadline = _parse_budget_seconds(budget_str)
    falsification_time = None
    if trigger_time is not None and deadline is not None:
        falsification_time = round(trigger_time + deadline, 2)
    elif "dt" in raw.get("observed", {}):
        dt = raw["observed"]["dt"]
        if trigger_time is not None:
            falsification_time = round(trigger_time + dt, 2)
    
    # For missing events with no budget, use last trace event time
    if falsification_time is None and trigger_time is not None:
        if trace_events:
            last_t = max(e["t"] for e in trace_events)
            falsification_time = round(last_t - t0, 2)

    # For negation violations, falsification is when the match was found
    if "NEG" in error_code and w_events["end"]:
        end_evt = w_events["end"].get("event", {})
        if "t" in end_evt:
            falsification_time = round(end_evt["t"] - t0, 2)

    # Determine expected and observed events
    expected_event = None
    observed_event = None
    
    if "NEG" in error_code:
        # Negation: the matched pattern IS the violation
        expected_event = "no_interruption"
        observed_event = "interruption_detected"
        if responsible == "unknown" and w_events["trigger"]:
            responsible = w_events["trigger"].get("event", {}).get("agent", "unknown")
    else:
        # Sequence / other: check right_event or end event
        end_data = w_events.get("end") or {}
        end_evt = end_data.get("event", {}) if end_data else {}
        obj = end_evt.get("object", "")
        if obj:
            expected_event = f"{end_evt.get('agent', '')}_{obj}"
            observed_event = expected_event  # Found but maybe late
        
        if "MISSING" in error_code:
            observed_event = None
            if not expected_event:
                expected_event = "expected_response"

    violated_op = _error_code_to_operator(error_code, operator)
    site = _clause_path_to_site(clause_path, error_code)

    return TransformedViolation(
        violation_id=f"v{violation_idx:03d}",
        violated_operator=violated_op,
        agent_attribution=responsible,
        site=site,
        trigger_event_id=trigger_event_id,
        expected_event=expected_event,
        observed_event=observed_event,
        deadline_seconds=deadline,
        trigger_time=trigger_time,
        falsification_time=falsification_time,
        error_code=error_code,
        clause_path=clause_path,
    )


# ---------------------------------------------------------------------------
# Counterexample Transformer
# ---------------------------------------------------------------------------

def transform_counterexample(
    audit_report: Dict,
    trace: Dict,
) -> Optional[Dict]:
    """
    Build a counterexample.json from a transformed audit report and trace.
    Returns None for SAT verdicts.
    """
    if audit_report["verdict"] == "SAT":
        return None

    violations = audit_report.get("violations", [])
    if not violations:
        return None

    v = violations[0]  # Primary violation
    events = trace.get("events", [])
    scenario_id = audit_report["scenario_id"]

    # Build evidence window
    trigger_time = v.get("trigger_time", 0)
    falsification_time = v.get("falsification_time")
    window_start = max(0, trigger_time - 0.5) if trigger_time else 0
    window_end = (falsification_time + 1.0) if falsification_time else (trigger_time + 5.0 if trigger_time else 5.0)

    window_events = []
    for evt in events:
        t = evt["timestamp"]
        if window_start <= t <= window_end:
            details = evt.get("object") or evt["event_type"]
            window_events.append({
                "event_id": evt["event_id"],
                "timestamp": evt["timestamp"],
                "event_type": evt["event_type"],
                "agent": evt["agent"],
                "details": details,
            })

    # Build trigger description
    trigger_time = trigger_time or 0
    trigger_desc = f"{v.get('violated_operator', 'obligation')} at {trigger_time}s"
    
    # Build expected description
    deadline = v.get("deadline_seconds")
    expected_window = ""
    if trigger_time is not None and deadline is not None:
        expected_window = f"({trigger_time}s, {trigger_time + deadline}s]"
    
    expected_event = v.get("expected_event") or "expected_response"
    
    # Build observed description
    observed_event = v.get("observed_event")
    if observed_event:
        observed_desc = f"{observed_event} observed"
    else:
        observed_desc = f"No {expected_event} observed before deadline"

    # Build falsification description
    fals_time = v.get("falsification_time") or 0
    fals_desc = f"Violation detected at {fals_time}s — {expected_event} not satisfied"

    # Build violated obligation string
    violated_obligation = (
        f"After {v.get('trigger_event_id', 'trigger')}, system must observe "
        f"{expected_event} within {deadline}s" if deadline
        else f"Contract operator '{v['violated_operator']}' must be satisfied"
    )

    cx = TransformedCounterexample(
        scenario_id=scenario_id,
        violation_id=v["violation_id"],
        violated_obligation=violated_obligation,
        trigger={
            "event_id": v.get("trigger_event_id", "unknown"),
            "time": trigger_time or 0,
            "description": trigger_desc,
        },
        expected={
            "event": expected_event,
            "time_window": expected_window,
        },
        observed={
            "event": observed_event,
            "description": observed_desc,
        },
        falsification={
            "time": fals_time,
            "description": fals_desc,
        },
        attribution=v["agent_attribution"],
        site=v.get("site"),
        evidence_window={
            "start": round(window_start, 2),
            "end": round(window_end, 2),
            "events": window_events,
        },
    )
    return asdict(cx)


# ---------------------------------------------------------------------------
# Metadata Generator
# ---------------------------------------------------------------------------

def generate_metadata_yaml(
    scenario_id: str,
    interaction_type: str,
    robot_platform: str,
    source_bag: Optional[str],
    contract_name: str,
) -> str:
    """Generate a metadata.yaml string for a scenario folder."""
    lines = [
        f"scenario_id: {scenario_id}",
        f"interaction_type: {interaction_type}",
        f"robot_platform: {robot_platform}",
        f"source_bag: {source_bag or 'synthetic'}",
        f"contract_name: {contract_name}",
        f"version: '1.0'",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Full Pipeline: JSONL trace + raw audit → scenario folder contents
# ---------------------------------------------------------------------------

def transform_scenario(
    scenario_id: str,
    contract_id: str,
    raw_trace_events: List[Dict],
    raw_audit: Dict,
    interaction_type: str = "Turn-taking / acknowledgment",
    robot_platform: str = "NAO",
    source_bag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full transformation pipeline. Returns a dict with all files needed for a scenario folder:
    {
        "trace.json": {...},
        "audit_report.json": {...},
        "counterexample.json": {...} or None,
        "metadata.yaml": "...",
    }
    """
    sorted_events = sorted(raw_trace_events, key=lambda e: e["t"])
    t0 = sorted_events[0]["t"] if sorted_events else 0.0

    trace = transform_trace(raw_trace_events, t0)
    audit_report = transform_audit_report(
        raw_audit, scenario_id, contract_id, sorted_events, t0
    )
    counterexample = transform_counterexample(audit_report, trace)
    metadata = generate_metadata_yaml(
        scenario_id, interaction_type, robot_platform, source_bag, contract_id
    )

    return {
        "trace.json": trace,
        "audit_report.json": audit_report,
        "counterexample.json": counterexample,
        "metadata.yaml": metadata,
    }
