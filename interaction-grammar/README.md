# Interaction Grammar Auditor

A deterministic interaction auditing engine for validating agent traces against interaction contracts.

## Installation

```bash
pip install -e .
```

## Usage

You can audit a trace against a contract using the `ig-audit` command (if installed) or by running the module directly.

### Command Line Interface

**Basic Usage:**

```bash
export PYTHONPATH=$PYTHONPATH:.
python3 src/cli/audit.py --contract <contract.json> --trace <trace.jsonl>
```

**Using the `ig-audit` command:**

```bash
ig-audit --contract <contract.json> --trace <trace.jsonl>
```

### Examples

**Successful Audit:**
```bash
python3 src/cli/audit.py --contract contracts/valid/seq_simple.json --trace debug_trace.jsonl
```

**Failed Audit (Invalid Trace):**
```bash
python3 src/cli/audit.py --contract contracts/valid/seq_simple.json --trace invalid_trace.jsonl
```

The auditor returns a JSON object with the verdict (`PASS` or `FAIL`) and detailed error information if a violation is found.
