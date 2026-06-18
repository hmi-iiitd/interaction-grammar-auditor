"""
This module serves as the Command Line Interface (CLI) for the Interaction Auditor.
It runs the auditing process for a given contract and trace file.
"""

import argparse
import sys
import json
from pathlib import Path
from src.compiler.parser import ContractParser
from src.compiler.validator import prepare_contract_for_validation
from src.audit.trace import Trace, TraceError
from src.audit.auditor import Auditor, AuditVerdict

def main():
    parser = argparse.ArgumentParser(description="Interaction Grammar Auditor")
    parser.add_argument("--contract", required=True, help="Path to the JSON contract file")
    parser.add_argument("--trace", required=True, help="Path to the JSONL trace file")
    args = parser.parse_args()

    contract_path = Path(args.contract)
    trace_path = Path(args.trace)

    if not contract_path.exists():
        print(f"Error: Contract file not found: {contract_path}", file=sys.stderr)
        sys.exit(1)
    
    if not trace_path.exists():
        print(f"Error: Trace file not found: {trace_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Load Contract
    try:
        with open(contract_path, 'r', encoding='utf-8-sig') as f:
            contract_data = json.load(f)
        prepare_contract_for_validation(contract_data)
        contract_parser = ContractParser()
        ast = contract_parser.parse(contract_data)
    except Exception as e:
        print(f"Error loading contract: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load Trace
    try:
        trace = Trace.from_file(str(trace_path))
    except TraceError as e:
        print(f"Error loading trace: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Audit
    auditor = Auditor(ast)
    result = auditor.audit(trace)

    # 4. Output
    print(json.dumps(result.to_dict(), indent=2))

    if result.verdict == AuditVerdict.PASS:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
