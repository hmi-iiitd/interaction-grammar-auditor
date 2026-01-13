import json
import sys
import traceback
from pathlib import Path

# Add interaction-grammar to sys.path
sys.path.append(str(Path(__file__).parent / "interaction-grammar"))

from src.compiler.validator import SchemaValidator
from src.compiler.parser import ContractParser
from src.compiler.ast import Act, Seq, Par, Repair, Bind
from jsonschema import ValidationError

VALID_CONTRACTS_DIR = Path("interaction-grammar/contracts/valid")
INVALID_CONTRACTS_DIR = Path("interaction-grammar/contracts/invalid")
SCHEMA_PATH = Path("interaction-grammar/schema/schema.json")

def test_schema_validation():
    print("Running Schema Validation Tests...")
    validator = SchemaValidator(str(SCHEMA_PATH))
    
    # Test Valid Contracts
    for contract_file in VALID_CONTRACTS_DIR.glob("*.json"):
        print(f"  Validating {contract_file.name}...", end=" ")
        with open(contract_file, 'r') as f:
            data = json.load(f)
        try:
            validator.validate(data)
            print("PASS")
        except ValidationError as e:
            print(f"FAIL: {e}")
            return False

    # Test Invalid Contracts
    for contract_file in INVALID_CONTRACTS_DIR.glob("*.json"):
        print(f"  Validating {contract_file.name} (expecting failure)...", end=" ")
        with open(contract_file, 'r') as f:
            data = json.load(f)
        try:
            validator.validate(data)
            print(f"FAIL: Expected ValidationError but got success")
            return False
        except ValidationError as e:
            print(f"PASS (Expected failure: {e.message})")
    return True

def test_compiler():
    print("\nRunning Compiler Tests...")
    parser = ContractParser()

    # Test Seq Simple
    try:
        print("  Testing seq_simple.json...", end=" ")
        with open(VALID_CONTRACTS_DIR / "seq_simple.json", 'r') as f:
            data = json.load(f)
        ast = parser.parse(data)
        assert isinstance(ast, Seq)
        assert ast.latency.value_ms == 2000.0
        assert isinstance(ast.left, Act)
        assert ast.left.prim == "σ"
        assert isinstance(ast.right, Act)
        assert ast.right.prim == "ρ"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()
        return False

    # Test Par Sync
    try:
        print("  Testing par_sync.json...", end=" ")
        with open(VALID_CONTRACTS_DIR / "par_sync.json", 'r') as f:
            data = json.load(f)
        ast = parser.parse(data)
        assert isinstance(ast, Par)
        assert ast.sync["start"].value_ms == 300.0
        assert isinstance(ast.left, Act)
        assert isinstance(ast.right, Act)
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()
        return False

    # Test Repair Retry
    try:
        print("  Testing repair_retry.json...", end=" ")
        with open(VALID_CONTRACTS_DIR / "repair_retry.json", 'r') as f:
            data = json.load(f)
        ast = parser.parse(data)
        assert isinstance(ast, Repair)
        assert ast.site == "reach"
        assert ast.retry.n_max == 2
        assert isinstance(ast.expr, Seq)
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()
        return False

    return True

def test_verifier():
    print("\nRunning Verifier Tests...")
    from src.compiler.verifier import ContractVerifier
    from src.compiler.constraint_parser import LatencyConstraint
    verifier = ContractVerifier()

    # Test Seq Valid
    try:
        print("  Testing Seq Valid...", end=" ")
        ast = Seq(
            left=Act("σ", "r", "c"),
            right=Act("ρ", "h", "c"),
            latency=LatencyConstraint(2000.0)
        )
        success, _ = verifier.verify(ast)
        assert success == True
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()
        return False

    # Test Seq Unsat
    try:
        print("  Testing Seq Unsat...", end=" ")
        ast = Seq(
            left=Act("σ", "r", "c"),
            right=Act("ρ", "h", "c"),
            latency=LatencyConstraint(-10.0)
        )
        success, reason = verifier.verify(ast)
        assert success == False
        print(f"PASS (Reason: {reason})")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = True
    if not test_schema_validation():
        success = False
    if not test_compiler():
        success = False
    if not test_verifier():
        success = False
    
    if success:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)
