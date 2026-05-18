"""Tests for Module E: Explanation Generator."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.explanation import generate_explanation, _template_explanation
from llm.mock import MockProvider


def test_explanation_sat():
    llm = MockProvider()
    result = generate_explanation(
        llm,
        scenario_id="pass_01",
        metadata={"interaction_type": "Test"},
        audit_report={"verdict": "SAT", "num_events": 5, "num_violations": 0, "violations": []},
        trace_events=[],
    )
    assert "passed" in result.lower()


def test_template_explanation_unsat():
    violation = {
        "violated_operator": "latency",
        "site": "timing",
        "trigger_event_id": "e001",
        "trigger_time": 0.0,
        "expected_event": "ack",
        "observed_event": "ack",
        "deadline_seconds": 8.0,
        "falsification_time": 8.0,
        "agent_attribution": "human_1",
    }
    result = _template_explanation("test_01", "UNSAT", violation)
    assert "latency" in result
    assert "e001" in result
    assert "8.0" in result
    assert "human_1" in result
    assert "template fallback" in result


def test_template_explanation_missing_observed():
    violation = {
        "violated_operator": "acknowledgment",
        "site": "closure",
        "trigger_event_id": "e003",
        "trigger_time": 3.5,
        "expected_event": "confirm",
        "observed_event": None,
        "deadline_seconds": None,
        "falsification_time": 5.0,
        "agent_attribution": "robot_1",
    }
    result = _template_explanation("test_02", "UNSAT", violation)
    assert "No matching event" in result
