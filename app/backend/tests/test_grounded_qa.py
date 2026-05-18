"""Tests for Module F: Grounded Q&A."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.grounded_qa import check_unsupported, template_answer
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class FakeScenario:
    scenario_id: str
    metadata: Dict[str, Any]
    trace: Dict[str, Any]
    audit_report: Dict[str, Any]
    counterexample: Optional[Dict[str, Any]] = None


def _make_scenario(verdict="UNSAT"):
    return FakeScenario(
        scenario_id="test_01",
        metadata={"interaction_type": "Turn-taking"},
        trace={"events": []},
        audit_report={
            "verdict": verdict,
            "num_events": 5,
            "num_violations": 1 if verdict == "UNSAT" else 0,
            "violations": [{
                "violation_id": "v001",
                "violated_operator": "latency",
                "trigger_event_id": "e001",
                "trigger_time": 0.0,
                "expected_event": "ack",
                "observed_event": "ack",
                "deadline_seconds": 8.0,
                "falsification_time": 8.0,
                "agent_attribution": "human_1",
                "clause_path": "$.items[0]",
            }] if verdict == "UNSAT" else [],
        },
        counterexample=None,
    )


def test_unsupported_question_confused():
    result = check_unsupported("Was the human confused?")
    assert result is not None
    assert "mental state" in result


def test_unsupported_question_frustrated():
    result = check_unsupported("Did the user get frustrated?")
    assert result is not None


def test_supported_question():
    result = check_unsupported("Why did this fail?")
    assert result is None


def test_template_why_fail():
    s = _make_scenario("UNSAT")
    answer = template_answer("Why did this fail?", s)
    assert "latency" in answer
    assert "0.0" in answer


def test_template_why_fail_sat():
    s = _make_scenario("SAT")
    answer = template_answer("Why did this fail?", s)
    assert "passed" in answer.lower()


def test_template_when_decidable():
    s = _make_scenario("UNSAT")
    answer = template_answer("When did the failure become decidable?", s)
    assert "8.0" in answer


def test_template_which_agent():
    s = _make_scenario("UNSAT")
    answer = template_answer("Which agent was attributed?", s)
    assert "human_1" in answer


def test_template_unknown_question():
    s = _make_scenario("UNSAT")
    answer = template_answer("What is the meaning of life?", s)
    assert "not present" in answer
