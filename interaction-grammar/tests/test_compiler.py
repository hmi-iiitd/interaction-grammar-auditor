import pytest
import json
from pathlib import Path
from src.compiler.parser import ContractParser
from src.compiler.ast import Act, Seq, Par, Repair, Bind

VALID_CONTRACTS_DIR = Path(__file__).parent.parent / "contracts" / "valid"

@pytest.fixture
def parser():
    return ContractParser()

def test_parse_seq_simple(parser):
    with open(VALID_CONTRACTS_DIR / "seq_simple.json", 'r') as f:
        data = json.load(f)
    ast = parser.parse(data)
    assert isinstance(ast, Seq)
    assert ast.latency.value_ms == 2000.0  # ≤2s -> 2000ms
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
