"""
This module serves as the Command Line Interface (CLI) for the Interaction Contract Compiler.
It orchestrates the validation and compilation process for a given JSON contract file.

Functions:
    - main: The main entry point for the CLI. It handles argument parsing, file loading, schema validation, AST compilation, and semantic validation.
"""

import argparse
import json
import sys
from pathlib import Path
from src.compiler.validator import SchemaValidator, SemanticValidator
from src.compiler.parser import ContractParser

def main():
    parser = argparse.ArgumentParser(description="Interaction Contract Compiler")
    parser.add_argument("contract", help="Path to the JSON contract file")
    args = parser.parse_args()

    contract_path = Path(args.contract)
    if not contract_path.exists():
        print(f"Error: File not found: {contract_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(contract_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # 1. Schema Validation
    schema_path = Path(__file__).parent.parent.parent / "schema" / "schema.json"
    validator = SchemaValidator(str(schema_path))
    try:
        validator.validate(data)
        print("Schema Validation Passed")
    except Exception as e:
        print(f"Schema Validation Failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Parse to AST
    parser = ContractParser()
    try:
        ast = parser.parse(data)
        print("AST Compilation Passed")
    except Exception as e:
        print(f"AST Compilation Failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Semantic Validation
    semantic_validator = SemanticValidator()
    try:
        semantic_validator.validate(ast)
        print("Semantic Validation Passed")
        print(f"Final AST: {ast}")
    except Exception as e:
        print(f"Semantic Validation Failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
