"""Tests for Transformer: audit_mapper."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from transformer.audit_mapper import (
    transform_trace, transform_audit_report, transform_counterexample,
    transform_scenario, _parse_budget_seconds,
)


def test_parse_budget_seconds():
    assert _parse_budget_seconds("≤8.0s") == 8.0
    assert _parse_budget_seconds("≤1.0s") == 1.0
    assert _parse_budget_seconds("<=500ms") == 0.5
    assert _parse_budget_seconds(None) is None


def test_transform_trace_relativizes_timestamps():
    raw = [
        {"t": 1000.0, "prim": "α", "agent": "robot_1", "channel": "speech", "object": "prompt"},
        {"t": 1002.5, "prim": "α", "agent": "human_1", "channel": "speech", "object": "ack"},
    ]
    result = transform_trace(raw)
    events = result["events"]
    assert events[0]["timestamp"] == 0.0
    assert events[1]["timestamp"] == 2.5
    assert events[0]["event_id"] == "e001"
    assert events[1]["event_id"] == "e002"


def test_transform_trace_generates_event_ids():
    raw = [{"t": float(i), "prim": "α", "agent": "r", "channel": "speech"} for i in range(5)]
    result = transform_trace(raw)
    ids = [e["event_id"] for e in result["events"]]
    assert ids == ["e001", "e002", "e003", "e004", "e005"]


def test_transform_audit_report_sat():
    raw_audit = {"verdict": "PASS"}
    result = transform_audit_report(raw_audit, "test", "c1", [], 0)
    assert result["verdict"] == "SAT"
    assert result["violations"] == []


def test_transform_audit_report_unsat():
    raw_audit = {
        "verdict": "FAIL",
        "operator": "sequence",
        "error_code": "V_SEQ_LATENCY_EXCEEDED",
        "clause_path": "$.items[0]",
        "budget": "≤8.0s",
        "observed": {"dt": 8.8},
        "responsible_agent": "human_1",
        "witness": {
            "left_event": {"idx": 0, "event": {"t": 100.0, "prim": "α", "agent": "robot_1"}},
            "right_event": {"idx": 3, "event": {"t": 108.8, "prim": "α", "agent": "human_1", "object": "ack"}},
        },
    }
    events = [{"t": 100.0}, {"t": 102.0}, {"t": 104.0}, {"t": 108.8}]
    result = transform_audit_report(raw_audit, "test", "c1", events, 100.0)
    assert result["verdict"] == "UNSAT"
    assert len(result["violations"]) == 1
    v = result["violations"][0]
    assert v["violated_operator"] == "latency"
    assert v["deadline_seconds"] == 8.0
    assert v["agent_attribution"] == "human_1"


def test_transform_counterexample_sat_returns_none():
    report = {"verdict": "SAT", "violations": []}
    trace = {"events": []}
    assert transform_counterexample(report, trace) is None


def test_transform_counterexample_unsat():
    report = {
        "verdict": "UNSAT",
        "scenario_id": "test",
        "violations": [{
            "violation_id": "v001", "violated_operator": "latency",
            "trigger_event_id": "e001", "trigger_time": 0.0,
            "expected_event": "ack", "observed_event": "ack",
            "deadline_seconds": 8.0, "falsification_time": 8.0,
            "agent_attribution": "human_1", "site": "timing",
        }],
    }
    trace = {"events": [
        {"event_id": "e001", "timestamp": 0.0, "event_type": "prompt",
         "agent": "robot_1", "object": "prompt"},
    ]}
    cx = transform_counterexample(report, trace)
    assert cx is not None
    assert cx["violation_id"] == "v001"
    assert cx["trigger"]["event_id"] == "e001"
    assert cx["falsification"]["time"] == 8.0


def test_full_transform_scenario():
    raw_events = [
        {"t": 500.0, "prim": "α", "agent": "robot_1", "channel": "speech", "object": "prompt"},
        {"t": 502.0, "prim": "α", "agent": "human_1", "channel": "speech", "object": "ack"},
    ]
    raw_audit = {"verdict": "PASS"}
    result = transform_scenario("test_01", "c1", raw_events, raw_audit)
    assert "trace.json" in result
    assert "audit_report.json" in result
    assert result["audit_report.json"]["verdict"] == "SAT"
    assert result["counterexample.json"] is None
    assert "metadata.yaml" in result
