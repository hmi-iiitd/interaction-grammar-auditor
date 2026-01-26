"""
This module contains unit tests for semantic validation of invalid contracts.
It ensures that the validator correctly identifies and reports semantic errors
with appropriate error codes.

Functions:
    - load_json: Helper function to load JSON files.
    - test_invalid_semantic_cases: Tests all invalid semantic cases against expected error codes.
"""

import json
from pathlib import Path
import pytest
from src.compiler.validator import ValidationError, SchemaValidator, SemanticValidator
from src.compiler.parser import ContractParser

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts" / "invalid_semantic"
EXPECTED = ROOT / "tests" / "fixtures" / "invalid_semantic_expected.json"
SCHEMA_PATH = ROOT / "schema" / "schema.json"

def load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def test_invalid_semantic_cases():
    expected = load_json(EXPECTED)
    schema_validator = SchemaValidator(str(SCHEMA_PATH))
    parser = ContractParser()
    semantic_validator = SemanticValidator()
    
    for fname, exp in expected.items():
        path = CONTRACTS / fname
        ast_data = load_json(path)
        
        # Try schema validation first (some errors caught here)
        try:
            schema_validator.validate(ast_data)
            # If schema passes, parse to AST
            ast = parser.parse(ast_data)
            # Then do semantic validation
            with pytest.raises(ValidationError) as e:
                semantic_validator.validate(ast)
        except ValidationError as e:
            err = e
        else:
            err = e.value
        
        assert err.code == exp["code"], f"{fname}: expected {exp['code']} got {err.code}"
        for frag in exp.get("message_contains", []):
            assert frag.lower() in err.message.lower(), f"{fname}: message missing '{frag}'"
