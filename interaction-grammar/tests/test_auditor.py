"""
Test suite for the Interaction Auditor.
Verifies trace loading, event matching, and auditing logic (Seq, Par).
"""

import pytest
import json
from pathlib import Path
from src.audit.trace import Trace, Event
from src.audit.matcher import EventMatcher
from src.audit.auditor import Auditor, AuditVerdict
from src.compiler.parser import ContractParser
from src.compiler.ast import Act

# Paths
TRACES_DIR = Path(__file__).parent.parent / "traces"
CONTRACTS_DIR = Path(__file__).parent.parent / "contracts" / "valid"

# --- Trace Tests ---
def test_trace_load_sort():
    t_path = TRACES_DIR / "valid" / "seq_pass.jsonl"
    trace = Trace.from_file(str(t_path))
    assert len(trace) == 2
    assert trace[0].t == 0.0
    assert trace[1].t == 1.2
    assert trace[0].prim == "σ"

def test_trace_filter():
    t_path = TRACES_DIR / "valid" / "seq_pass.jsonl"
    trace = Trace.from_file(str(t_path))
    robot_trace = trace.filter(agent="robot_1")
    assert len(robot_trace) == 1
    assert robot_trace[0].agent == "robot_1"

# --- Matcher Tests ---
def test_matcher_basic():
    act = Act(prim="σ", agent="r1", channel="c1", object="o1")
    evt = Event(t=0, prim="σ", agent="r1", channel="c1", object="o1")
    assert EventMatcher.match_act(act, evt)

def test_matcher_mismatch_prim():
    act = Act(prim="σ", agent="r1", channel="c1")
    evt = Event(t=0, prim="ρ", agent="r1", channel="c1")
    assert not EventMatcher.match_act(act, evt)

def test_matcher_agent_list():
    act = Act(prim="σ", agent=["r1", "r2"], channel="c1")
    evt1 = Event(t=0, prim="σ", agent="r1", channel="c1")
    evt2 = Event(t=0, prim="σ", agent="r2", channel="c1")
    evt3 = Event(t=0, prim="σ", agent="r3", channel="c1")
    
    assert EventMatcher.match_act(act, evt1)
    assert EventMatcher.match_act(act, evt2)
    assert not EventMatcher.match_act(act, evt3)

def test_matcher_optional_object():
    # Contract has no object -> wildmatch
    act = Act(prim="σ", agent="r1", channel="c1", object=None)
    evt = Event(t=0, prim="σ", agent="r1", channel="c1", object="anything")
    assert EventMatcher.match_act(act, evt)
    
    # Contract has object -> exact match
    act.object = "specific"
    assert not EventMatcher.match_act(act, evt)
    evt.object = "specific"
    assert EventMatcher.match_act(act, evt)

# --- Auditor Tests ---
@pytest.fixture
def parser():
    return ContractParser()

def test_audit_seq_pass(parser):
    with open(CONTRACTS_DIR / "seq_simple.json") as f:
        ast = parser.parse(json.load(f))
    
    trace = Trace.from_file(str(TRACES_DIR / "valid" / "seq_pass.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)
    
    assert result.verdict == AuditVerdict.PASS
    # Witness checks
    assert result.witness["idx"] == 1 # Ends at index 1

def test_audit_seq_fail_latency(parser):
    with open(CONTRACTS_DIR / "seq_simple.json") as f:
        ast = parser.parse(json.load(f))
        
    trace = Trace.from_file(str(TRACES_DIR / "invalid" / "seq_fail_latency.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)
    
    assert result.verdict == AuditVerdict.FAIL
    assert result.code == "V_SEQ_LATENCY"
    assert result.observed.get("dt") > 2.0

def test_audit_seq_missing_right(parser):
    with open(CONTRACTS_DIR / "seq_simple.json") as f:
        ast = parser.parse(json.load(f))
        
    trace = Trace.from_file(str(TRACES_DIR / "invalid" / "seq_fail_missing_right.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)
    
    assert result.verdict == AuditVerdict.FAIL
    assert result.code == "V_SEQ_MISSING_RIGHT"

def test_audit_par_pass(parser):
    with open(CONTRACTS_DIR / "par_sync.json") as f:
        ast = parser.parse(json.load(f))
        
    trace = Trace.from_file(str(TRACES_DIR / "valid" / "par_pass.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)
    
    assert result.verdict == AuditVerdict.PASS

def test_audit_par_fail_sync(parser):
    with open(CONTRACTS_DIR / "par_sync.json") as f:
        ast = parser.parse(json.load(f))
        
    trace = Trace.from_file(str(TRACES_DIR / "invalid" / "par_fail_sync.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)
    
    assert result.verdict == AuditVerdict.FAIL
    assert result.code == "V_PAR_SYNC_START"

# --- Neg Tests ---
def test_audit_neg_pass(parser):
    with open(CONTRACTS_DIR / "neg_simple.json") as f:
        ast = parser.parse(json.load(f))

    trace = Trace.from_file(str(TRACES_DIR / "valid" / "neg_pass.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)

    assert result.verdict == AuditVerdict.PASS
    assert result.witness.get("neg") is True

def test_audit_neg_fail(parser):
    with open(CONTRACTS_DIR / "neg_simple.json") as f:
        ast = parser.parse(json.load(f))

    trace = Trace.from_file(str(TRACES_DIR / "invalid" / "neg_fail.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)

    assert result.verdict == AuditVerdict.FAIL
    assert result.code == "V_NEG_VIOLATED"

# --- Bind Tests ---
def test_audit_bind_pass(parser):
    with open(CONTRACTS_DIR / "bind_simple.json") as f:
        ast = parser.parse(json.load(f))

    trace = Trace.from_file(str(TRACES_DIR / "valid" / "bind_pass.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)

    assert result.verdict == AuditVerdict.PASS

def test_audit_bind_fail_missing(parser):
    with open(CONTRACTS_DIR / "bind_simple.json") as f:
        ast = parser.parse(json.load(f))

    trace = Trace.from_file(str(TRACES_DIR / "invalid" / "bind_fail_missing.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)

    assert result.verdict == AuditVerdict.FAIL
    assert result.code == "V_BIND_ITEM_MISSING"

def test_audit_bind_fail_latency(parser):
    with open(CONTRACTS_DIR / "bind_simple.json") as f:
        ast = parser.parse(json.load(f))

    trace = Trace.from_file(str(TRACES_DIR / "invalid" / "bind_fail_latency.jsonl"))
    auditor = Auditor(ast)
    result = auditor.audit(trace)

    assert result.verdict == AuditVerdict.FAIL
    assert result.code == "V_BIND_LATENCY"
    assert result.observed.get("span") > 1.0
