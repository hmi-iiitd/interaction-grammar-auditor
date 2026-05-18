"""Tests for Module D: Prompt Builder."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.prompt_builder import build_explanation_prompt, build_qa_prompt


def test_explanation_prompt_structure():
    sys_prompt, user_prompt = build_explanation_prompt(
        scenario_id="test_01",
        metadata={"interaction_type": "Turn-taking", "robot_platform": "NAO"},
        verdict="UNSAT",
        violation={
            "violation_id": "v001", "violated_operator": "latency",
            "trigger_event_id": "e001", "trigger_time": 0.0,
            "expected_event": "ack", "observed_event": "ack",
            "deadline_seconds": 8.0, "falsification_time": 8.0,
            "agent_attribution": "human_1", "site": "timing",
            "error_code": "V_SEQ_LATENCY_EXCEEDED",
        },
        evidence_events=[
            {"event_id": "e001", "timestamp": 0.0, "agent": "robot_1",
             "event_type": "prompt", "primitive": "α"},
        ],
    )
    assert "MUST NOT infer" in sys_prompt
    assert "test_01" in user_prompt
    assert "latency" in user_prompt
    assert "e001" in user_prompt


def test_explanation_prompt_sat():
    sys_prompt, user_prompt = build_explanation_prompt(
        scenario_id="pass_01",
        metadata={"interaction_type": "Test"},
        verdict="SAT",
        violation=None,
        evidence_events=[],
    )
    assert "SAT" in user_prompt


def test_qa_prompt_includes_question():
    sys_prompt, user_prompt = build_qa_prompt(
        question="Why did this fail?",
        scenario_id="test_01",
        metadata={"interaction_type": "Turn-taking"},
        audit_report={"verdict": "UNSAT", "contract_id": "c1",
                      "num_events": 5, "num_violations": 1,
                      "violations": [{"violation_id": "v001",
                                      "violated_operator": "latency",
                                      "trigger_event_id": "e001",
                                      "trigger_time": 0.0,
                                      "expected_event": "ack",
                                      "observed_event": "ack",
                                      "deadline_seconds": 8.0,
                                      "falsification_time": 8.0,
                                      "agent_attribution": "human_1"}]},
        counterexample=None,
        trace_events=[],
    )
    assert "Why did this fail?" in user_prompt
    assert "MUST NOT" in sys_prompt


def test_qa_prompt_truncates_long_traces():
    events = [
        {"event_id": f"e{i:03d}", "timestamp": float(i), "agent": "r",
         "event_type": "act", "primitive": "α"}
        for i in range(30)
    ]
    _, user_prompt = build_qa_prompt(
        question="Summary?",
        scenario_id="long",
        metadata={},
        audit_report={"verdict": "SAT", "num_events": 30, "num_violations": 0, "violations": []},
        counterexample=None,
        trace_events=events,
    )
    assert "10 more events" in user_prompt
