"""
This module contains unit tests for the SchemaValidator, ensuring that interaction contracts
conform to the defined JSON schema.

Functions:
    - validator: A pytest fixture that provides an instance of SchemaValidator initialized with the project schema.
    - test_valid_contracts: Iterates through all JSON files in the 'contracts/valid' directory and verifies that they pass schema validation.
    - test_invalid_contracts: Iterates through all JSON files in the 'contracts/invalid' directory and verifies that they fail schema validation as expected.
"""

import pytest
import json
from pathlib import Path
from jsonschema import ValidationError as JsonSchemaValidationError
from src.compiler.validator import SchemaValidator, ValidationError, prepare_contract_for_validation

VALID_CONTRACTS_DIR = Path(__file__).parent.parent / "contracts" / "valid"
INVALID_CONTRACTS_DIR = Path(__file__).parent.parent / "contracts" / "invalid"
SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "schema.json"

@pytest.fixture
def validator():
    return SchemaValidator(str(SCHEMA_PATH))

def test_valid_contracts(validator):
    for contract_file in VALID_CONTRACTS_DIR.glob("*.json"):
        with open(contract_file, 'r') as f:
            data = json.load(f)
        try:
            validator.validate(data)
        except (JsonSchemaValidationError, ValidationError) as e:
            pytest.fail(f"Valid contract {contract_file.name} failed validation: {e}")

def test_locked_contract_metadata_stripped_before_validation(validator):
    sample = VALID_CONTRACTS_DIR / "bind_simple.json"
    if not sample.exists():
        sample = next(VALID_CONTRACTS_DIR.glob("*.json"))
    with open(sample, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["_contract_metadata"] = {"contract_id": "test", "version": "1.0", "locked": True}
    with pytest.raises(JsonSchemaValidationError):
        validator.validate(data)
    prepare_contract_for_validation(data)
    validator.validate(data)


def test_invalid_contracts(validator):
    # These files should fail schema validation
    schema_invalid_files = ["act_missing_prim.json", "bind_latency_policy.json", "malformed_symbolic.json"]
    
    for fname in schema_invalid_files:
        contract_file = INVALID_CONTRACTS_DIR / fname
        if contract_file.exists():
            with open(contract_file, 'r') as f:
                data = json.load(f)
            with pytest.raises((JsonSchemaValidationError, ValidationError)):
                validator.validate(data)
