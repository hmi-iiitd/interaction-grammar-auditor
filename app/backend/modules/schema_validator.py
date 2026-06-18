"""
Module B: Schema Validator

Validates trace, contract, audit report, and counterexample files
against expected JSON schemas. Rejects invalid files before reaching
the explanation layer.
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, Any, List, Optional


class SchemaValidationError(Exception):
    """Raised when a file fails schema validation."""
    def __init__(self, file_type: str, message: str):
        self.file_type = file_type
        self.message = message
        super().__init__(f"[{file_type}] {message}")


# Load schemas once
_SCHEMA_DIR = Path(__file__).parent.parent / "schemas"


def _load_schema(name: str) -> Dict:
    path = _SCHEMA_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_SCHEMAS = {}


def _get_schema(name: str) -> Dict:
    if name not in _SCHEMAS:
        _SCHEMAS[name] = _load_schema(name)
    return _SCHEMAS[name]


def validate_trace(trace: Dict[str, Any]) -> None:
    """Validate a trace against the trace schema."""
    schema = _get_schema("trace.schema.json")
    try:
        jsonschema.validate(instance=trace, schema=schema)
    except jsonschema.ValidationError as e:
        raise SchemaValidationError("trace", e.message)


def validate_audit_report(report: Dict[str, Any]) -> None:
    """Validate an audit report against the audit report schema."""
    schema = _get_schema("audit_report.schema.json")
    try:
        jsonschema.validate(instance=report, schema=schema)
    except jsonschema.ValidationError as e:
        raise SchemaValidationError("audit_report", e.message)


def validate_counterexample(counterexample: Dict[str, Any]) -> None:
    """Validate a counterexample against the counterexample schema."""
    schema = _get_schema("counterexample.schema.json")
    try:
        jsonschema.validate(instance=counterexample, schema=schema)
    except jsonschema.ValidationError as e:
        raise SchemaValidationError("counterexample", e.message)


def validate_scenario(scenario) -> List[str]:
    """
    Validate all files in a ScenarioPackage.
    Returns a list of error messages (empty if all valid).
    """
    errors = []

    try:
        validate_trace(scenario.trace)
    except SchemaValidationError as e:
        errors.append(str(e))

    try:
        validate_audit_report(scenario.audit_report)
    except SchemaValidationError as e:
        errors.append(str(e))

    if scenario.counterexample:
        try:
            validate_counterexample(scenario.counterexample)
        except SchemaValidationError as e:
            errors.append(str(e))

    return errors