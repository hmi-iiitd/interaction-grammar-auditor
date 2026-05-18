"""Tests for Module C: Evidence Extractor."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.evidence_extractor import extract_evidence, extract_all_evidence


def _make_trace():
    return {"events": [
        {"event_id": "e001", "timestamp": 0.0, "agent": "robot_1", "event_type": "prompt", "primitive": "α", "modality": "speech"},
        {"event_id": "e002", "timestamp": 2.0, "agent": "human_1", "event_type": "speaking_start", "primitive": "σ", "modality": "speech"},
        {"event_id": "e003", "timestamp": 4.0, "agent": "human_1", "event_type": "speaking_end", "primitive": "ρ", "modality": "speech"},
        {"event_id": "e004", "timestamp": 5.0, "agent": "human_1", "event_type": "ack", "primitive": "α", "modality": "speech", "object": "ack"},
        {"event_id": "e005", "timestamp": 6.0, "agent": "robot_1", "event_type": "confirm", "primitive": "α", "modality": "speech", "object": "confirm"},
    ]}


def test_extract_evidence_basic():
    trace = _make_trace()
    violation = {
        "trigger_event_id": "e001",
        "trigger_time": 0.0,
        "falsification_time": 8.0,
        "expected_event": "ack",
        "observed_event": "ack",
        "deadline_seconds": 8.0,
    }
    ev = extract_evidence(trace, violation)
    assert ev["trigger_event"]["event_id"] == "e001"
    assert ev["trigger_time"] == 0.0
    assert ev["falsification_time"] == 8.0
    assert len(ev["window_events"]) == 5  # all events in window


def test_extract_evidence_narrow_window():
    trace = _make_trace()
    violation = {
        "trigger_event_id": "e003",
        "trigger_time": 4.0,
        "falsification_time": 5.5,
        "expected_event": "ack",
        "observed_event": None,
    }
    ev = extract_evidence(trace, violation, context_margin=0.5)
    assert ev["window_start"] == 3.5
    assert ev["window_end"] == 6.0
    assert len(ev["window_events"]) == 3  # e003, e004, e005


def test_extract_all_evidence_sat():
    trace = _make_trace()
    audit = {"verdict": "SAT", "violations": []}
    result = extract_all_evidence(trace, audit)
    assert result == []
