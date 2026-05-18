"""Tests for Module B: Schema Validator."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from modules.schema_validator import (
    validate_trace, validate_audit_report, validate_counterexample,
    SchemaValidationError,
)


def test_valid_trace():
    trace = {"events": [
        {"event_id": "e001", "timestamp": 0.0, "agent": "robot_1",
         "event_type": "prompt", "primitive": "α", "modality": "speech"}
    ]}
    validate_trace(trace)  # should not raise


def test_trace_missing_events():
    with pytest.raises(SchemaValidationError):
        validate_trace({})


def test_trace_bad_event_id():
    trace = {"events": [
        {"event_id": "BAD", "timestamp": 0.0, "agent": "robot_1",
         "event_type": "prompt", "primitive": "α", "modality": "speech"}
    ]}
    with pytest.raises(SchemaValidationError):
        validate_trace(trace)


def test_valid_audit_report():
    report = {"scenario_id": "test", "contract_id": "c1", "verdict": "SAT"}
    validate_audit_report(report)  # should not raise


def test_audit_bad_verdict():
    report = {"scenario_id": "test", "contract_id": "c1", "verdict": "MAYBE"}
    with pytest.raises(SchemaValidationError):
        validate_audit_report(report)


def test_valid_counterexample():
    cx = {
        "scenario_id": "test", "violation_id": "v001",
        "violated_obligation": "must ack within 8s",
        "trigger": {"event_id": "e001", "time": 0.0, "description": "prompt"},
        "expected": {"event": "ack", "time_window": "(0s, 8s]"},
        "observed": {"description": "no ack observed"},
        "falsification": {"time": 8.0, "description": "deadline passed"},
    }
    validate_counterexample(cx)  # should not raise
