import argparse
import json
import sys
from pathlib import Path
from src.compiler.validator import SchemaValidator
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
        print(f"AST: {ast}")
    except Exception as e:
        print(f"AST Compilation Failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Z3 Verification
    from src.compiler.verifier import ContractVerifier
    verifier = ContractVerifier()
    try:
    try:
        success, reason = verifier.verify(ast)
        if success:
            print(f"Z3 Verification Passed: {reason}")
        else:
            print(f"Z3 Verification Failed: {reason}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Z3 Verification Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
