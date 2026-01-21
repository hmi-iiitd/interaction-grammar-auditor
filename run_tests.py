"""
This script orchestrates the execution of the entire test suite for the Interaction Contract Compiler.
It verifies schema validation, AST compilation, and semantic correctness using a set of valid and invalid contract fixtures.

Functions:
    - test_schema_validation: Iterates through valid and invalid fixtures to verify that the SchemaValidator correctly identifies valid contracts and reports errors for invalid ones.
    - test_compiler: Verifies that the ContractParser correctly converts valid JSON fixtures into the expected AST structures and fails for malformed inputs.
    - test_semantic_validation: Performs deep semantic checks on both manually constructed AST nodes and those parsed from fixtures to ensure logical constraints (e.g., agent naming) are enforced.

Execution:
    - The script runs all three test functions and exits with code 0 if all pass, or code 1 if any fail.
"""

import json
import sys
import traceback
from pathlib import Path

# Add interaction-grammar to sys.path
sys.path.append(str(Path(__file__).parent / "interaction-grammar"))

from src.compiler.validator import SchemaValidator, SemanticValidator
from src.compiler.parser import ContractParser
from src.compiler.ast import Act, Seq, Par, Repair, Bind, Neg
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
        if contract_file.name in ["invalid_agent_type.json", "malformed_symbolic.json"]:
            continue # These are for semantic/compiler validation, not schema
        
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

    # Test Malformed Symbolic (Grammar failure)
    try:
        print("  Testing malformed_symbolic.json (expecting failure)...", end=" ")
        with open(INVALID_CONTRACTS_DIR / "malformed_symbolic.json", 'r') as f:
            data = json.load(f)
        try:
            parser.parse(data)
            print("FAIL: Expected grammar error")
            return False
        except Exception as e:
            print(f"PASS (Expected failure: {e})")
    except Exception as e:
        print(f"FAIL: {e}")
        return False

    return True

def test_semantic_validation():
    print("\nRunning Semantic Validation Tests...")
    validator = SemanticValidator()
    parser = ContractParser()

    # Test Valid Act
    try:
        print("  Testing Valid Act...", end=" ")
        act = Act(prim="σ", agent="robot_1", channel="speech")
        validator.validate(act)
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        return False

    # Test Invalid Agent Format
    try:
        print("  Testing Invalid Agent Format...", end=" ")
        act = Act(prim="σ", agent="robot1", channel="speech")
        try:
            validator.validate(act)
            print("FAIL: Expected ValueError")
            return False
        except ValueError:
            print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        return False

    # Test Invalid Agent Type from fixture
    try:
        print("  Testing Invalid Agent Type (fixture)...", end=" ")
        with open(INVALID_CONTRACTS_DIR / "invalid_agent_type.json", 'r') as f:
            data = json.load(f)
        ast = parser.parse(data)
        try:
            validator.validate(ast)
            print("FAIL: Expected ValueError")
            return False
        except ValueError as e:
            print(f"PASS (Expected failure: {e})")
    except Exception as e:
        print(f"FAIL: {e}")
        return False

    return True

if __name__ == "__main__":
    success = True
    if not test_schema_validation():
        success = False
    if not test_compiler():
        success = False
    if not test_semantic_validation():
        success = False
    
    if success:
        print("\nAll tests passed!")
        sys.exit(0)
    print("\ntest failed.")
    sys.exit(1)
