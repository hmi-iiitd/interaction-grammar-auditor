"""Tests for Module G: Report Generator."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.report_generator import generate_markdown_report, generate_json_report
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class FakeScenario:
    scenario_id: str
    metadata: Dict[str, Any]
    trace: Dict[str, Any]
    contract: Dict[str, Any]
    audit_report: Dict[str, Any]
    counterexample: Optional[Dict[str, Any]] = None


def _make_scenario(verdict="UNSAT"):
    violations = [{
        "violation_id": "v001", "violated_operator": "latency",
        "agent_attribution": "human_1", "site": "timing",
        "trigger_event_id": "e001", "trigger_time": 0.0,
        "expected_event": "ack", "observed_event": "ack",
        "deadline_seconds": 8.0, "falsification_time": 8.0,
        "error_code": "V_SEQ_LATENCY_EXCEEDED", "clause_path": "$.items[0]",
    }] if verdict == "UNSAT" else []

    return FakeScenario(
        scenario_id="test_01",
        metadata={"interaction_type": "Turn-taking", "robot_platform": "NAO",
                  "source_bag": "test.bag"},
        trace={"events": [
            {"event_id": "e001", "timestamp": 0.0, "agent": "robot_1",
             "event_type": "prompt", "primitive": "α", "modality": "speech",
             "object": "prompt"},
        ]},
        contract={"node": "bind", "items": []},
        audit_report={"scenario_id": "test_01", "contract_id": "c1",
                     "verdict": verdict, "num_events": 1,
                     "num_violations": len(violations),
                     "violations": violations},
    )


def test_markdown_report_sat():
    s = _make_scenario("SAT")
    md = generate_markdown_report(s)
    assert "# Scenario Audit Report" in md
    assert "✅ **SAT**" in md
    assert "test_01" in md


def test_markdown_report_unsat():
    s = _make_scenario("UNSAT")
    md = generate_markdown_report(s)
    assert "❌ **UNSAT**" in md
    assert "latency" in md
    assert "v001" in md


def test_json_report_structure():
    s = _make_scenario("UNSAT")
    report = generate_json_report(s)
    assert report["scenario_id"] == "test_01"
    assert report["verdict"] == "UNSAT"
    assert report["num_violations"] == 1
    assert "generated_at" in report


def test_json_report_sat():
    s = _make_scenario("SAT")
    report = generate_json_report(s)
    assert report["verdict"] == "SAT"
    assert report["num_violations"] == 0
