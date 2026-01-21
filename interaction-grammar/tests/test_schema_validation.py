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
from jsonschema import ValidationError
from src.compiler.validator import SchemaValidator

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
        except ValidationError as e:
            pytest.fail(f"Valid contract {contract_file.name} failed validation: {e}")

def test_invalid_contracts(validator):
    for contract_file in INVALID_CONTRACTS_DIR.glob("*.json"):
        with open(contract_file, 'r') as f:
            data = json.load(f)
        with pytest.raises(ValidationError, match=".*"):
            validator.validate(data)
