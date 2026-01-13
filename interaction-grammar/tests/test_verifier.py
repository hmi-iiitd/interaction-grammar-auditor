import pytest
from src.compiler.verifier import ContractVerifier
from src.compiler.ast import Act, Seq, Par, Repair
from src.compiler.constraint_parser import LatencyConstraint, SyncConstraint

@pytest.fixture
def verifier():
    return ContractVerifier()

def test_verify_seq_valid(verifier):
    # Seq with ample latency
    ast = Seq(
        left=Act("σ", "r", "c"),
        right=Act("ρ", "h", "c"),
        latency=LatencyConstraint(2000.0)
    )
    success, _ = verifier.verify(ast)
    assert success == True

def test_verify_seq_unsatisfiable(verifier):
    # Seq with impossible latency (negative or too tight if we had duration estimates)
    # Since we don't have duration estimates for Acts yet, basic Seq is always satisfiable unless latency < 0
    ast = Seq(
        left=Act("σ", "r", "c"),
        right=Act("ρ", "h", "c"),
        latency=LatencyConstraint(-10.0)
    )
    success, reason = verifier.verify(ast)
    assert success == False
    assert "unsatisfiable" in reason

def test_verify_par_valid(verifier):
    ast = Par(
        left=Act("σ", "r", "c"),
        right=Act("ρ", "h", "c"),
        sync={"start": SyncConstraint("start", 100.0)}
    )
    success, _ = verifier.verify(ast)
    assert success == True
