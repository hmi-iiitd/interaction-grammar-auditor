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
