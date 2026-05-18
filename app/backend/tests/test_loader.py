"""Tests for Module A: Scenario Loader."""

import json
import tempfile
import os
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.loader import load_scenario, load_all_scenarios, LoaderError


def _make_scenario(tmp, scenario_id="test_01", verdict="SAT", violations=None):
    """Helper to create a minimal valid scenario folder."""
    sdir = Path(tmp) / scenario_id
    (sdir / "raw").mkdir(parents=True)
    (sdir / "traces").mkdir(parents=True)
    (sdir / "contracts").mkdir(parents=True)
    (sdir / "audits").mkdir(parents=True)

    trace = {"events": [
        {"event_id": "e001", "timestamp": 0.0, "agent": "robot_1",
         "event_type": "prompt", "primitive": "α", "modality": "speech"}
    ]}
    with open(sdir / "traces" / "trace.json", "w") as f:
        json.dump(trace, f)

    contract = {"node": "bind", "items": []}
    with open(sdir / "contracts" / "contract.ig.json", "w") as f:
        json.dump(contract, f)

    audit = {"scenario_id": scenario_id, "contract_id": "test_v1",
             "verdict": verdict, "num_events": 1, "num_violations": 0,
             "violations": violations or []}
    with open(sdir / "audits" / "audit_report.json", "w") as f:
        json.dump(audit, f)

    with open(sdir / "metadata.yaml", "w") as f:
        f.write(f"scenario_id: {scenario_id}\ninteraction_type: test\n")

    return str(sdir)


def test_load_valid_scenario():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_scenario(tmp)
        pkg = load_scenario(path)
        assert pkg.scenario_id == "test_01"
        assert pkg.trace["events"][0]["event_id"] == "e001"
        assert pkg.audit_report["verdict"] == "SAT"
        assert pkg.counterexample is None


def test_load_missing_trace_raises():
    with tempfile.TemporaryDirectory() as tmp:
        path = _make_scenario(tmp, "bad_01")
        os.remove(Path(path) / "traces" / "trace.json")
        with pytest.raises(LoaderError, match="Missing required file"):
            load_scenario(path)


def test_load_nonexistent_folder_raises():
    with pytest.raises(LoaderError, match="not found"):
        load_scenario("/nonexistent/path")


def test_load_all_scenarios():
    with tempfile.TemporaryDirectory() as tmp:
        _make_scenario(tmp, "s1")
        _make_scenario(tmp, "s2", verdict="UNSAT")
        scenarios = load_all_scenarios(tmp)
        assert len(scenarios) == 2
        ids = {s.scenario_id for s in scenarios}
        assert ids == {"s1", "s2"}
