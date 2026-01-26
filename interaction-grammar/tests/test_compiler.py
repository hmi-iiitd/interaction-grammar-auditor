"""
This module contains unit tests for the ContractParser, ensuring that interaction contracts
are correctly parsed into their corresponding AST structures.

Functions:
    - parser: A pytest fixture that provides an instance of ContractParser.
    - test_parse_seq_simple: Verifies parsing of a simple sequential interaction with numeric latency.
    - test_parse_par_sync: Verifies parsing of parallel interactions with synchronization constraints.
    - test_parse_repair_retry: Verifies parsing of repair sites with numeric retry policies.
    - test_parse_neg: Verifies parsing of negation/disruption nodes.
    - test_parse_retry_string: Verifies parsing of string-based retry specifications (e.g., N≤3,μ≤0.5).
    - test_parse_symbolic_latency: Verifies parsing of symbolic latency constraints (e.g., Δ(t1, t2)).
    - test_parse_agent_group_string: Verifies parsing of agent groups defined as strings (e.g., [robot_1, human_1]).
"""

import pytest
import json
from pathlib import Path
from src.compiler.parser import ContractParser, ParserError
from src.compiler.constraint_parser import ConstraintError
from src.compiler.ast import Act, Seq, Par, Repair, Bind, Neg

VALID_CONTRACTS_DIR = Path(__file__).parent.parent / "contracts" / "valid"

@pytest.fixture
def parser():
    return ContractParser()

def test_parse_seq_simple(parser):
    with open(VALID_CONTRACTS_DIR / "seq_simple.json", 'r') as f:
        data = json.load(f)
    ast = parser.parse(data)
    assert isinstance(ast, Seq)
    assert ast.latency.value_ms == 2000.0
    assert isinstance(ast.left, Act)
    assert ast.left.prim == "σ"
    assert isinstance(ast.right, Act)
    assert ast.right.prim == "ρ"

def test_parse_par_sync(parser):
    with open(VALID_CONTRACTS_DIR / "par_sync.json", 'r') as f:
        data = json.load(f)
    ast = parser.parse(data)
    assert isinstance(ast, Par)
    assert ast.sync["start"].value_ms == 300.0
    assert isinstance(ast.left, Act)
    assert isinstance(ast.right, Act)

def test_parse_repair_retry(parser):
    with open(VALID_CONTRACTS_DIR / "repair_retry.json", 'r') as f:
        data = json.load(f)
    ast = parser.parse(data)
    assert isinstance(ast, Repair)
    assert ast.site == "reach"
    assert ast.retry.n_max == 2
    assert isinstance(ast.expr, Seq)

def test_parse_neg(parser):
    data = {
        "node": "neg",
        "expr": {
            "node": "act",
            "prim": "σ",
            "agent": "robot_1",
            "channel": "speech"
        },
        "disrupt": "ϵ"
    }
    ast = parser.parse(data)
    assert isinstance(ast, Neg)
    assert isinstance(ast.expr, Act)
    assert ast.disrupt == "ϵ"

def test_parse_retry_string(parser):
    data = {
        "node": "repair",
        "site": "reach",
        "expr": {
            "node": "act",
            "prim": "σ",
            "agent": "robot_1",
            "channel": "speech"
        },
        "retry": "N≤3,μ≤0.5"
    }
    ast = parser.parse(data)
    assert isinstance(ast, Repair)
    assert ast.retry.n_max == 3
    assert ast.retry.mu_max == 0.5

def test_parse_symbolic_latency(parser):
    data = {
        "node": "seq",
        "left": {"node": "act", "prim": "σ", "agent": "robot_1", "channel": "c"},
        "right": {"node": "act", "prim": "ρ", "agent": "human_1", "channel": "c"},
        "latency": "Δ(t1, t2)"
    }
    ast = parser.parse(data)
    assert ast.latency.symbolic == "Δ(t1,t2)"

def test_parse_agent_group_string(parser):
    data = {
        "node": "act",
        "prim": "σ",
        "agent": "[robot_1, human_1]",
        "channel": "c"
    }
    ast = parser.parse(data)
    assert isinstance(ast.agent, list)
    assert "robot_1" in ast.agent
    assert "human_1" in ast.agent

def test_parse_missing_node_type(parser):
    data = {
        "prim": "σ",
        "agent": "robot_1",
        "channel": "speech"
    }
    with pytest.raises(ParserError) as e:
        parser.parse(data)
    assert e.value.code == "E_NODE_TYPE_MISSING"

def test_parse_unknown_node_type(parser):
    data = {
        "node": "unknown_type",
        "agent": "robot_1"
    }
    with pytest.raises(ParserError) as e:
        parser.parse(data)
    assert e.value.code == "E_UNKNOWN_NODE_TYPE"
