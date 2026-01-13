# Interaction Contract Compiler

This project implements a compiler and verifier for Interaction Contracts, a formal specification language for human-robot interaction (HRI). The compiler validates JSON-based interaction contracts against a schema, parses them into an Abstract Syntax Tree (AST), and performs formal verification of temporal and logical constraints using the Z3 theorem prover.

## Features

*   **Schema Validation**: Validates input JSON contracts against a rigorous JSON Schema to ensure structural correctness.
*   **Grammar-Based Parsing**: Utilizes the Lark parsing library to parse complex constraint strings (e.g., latency, synchronization, retry policies) defined in the authoritative grammar.
*   **Abstract Syntax Tree (AST)**: Compiles the raw JSON into a typed AST representing the interaction logic (Sequences, Parallels, Repairs, Actions).
*   **Formal Verification**: Encodes the AST and its constraints into Satisfiability Modulo Theories (SMT) formulas and uses the Z3 solver to verify satisfiability. It detects logical contradictions such as impossible latency constraints or conflicting synchronization requirements.
*   **Error Reporting**: Provides detailed error messages, including specific schema violations and "unsatisfiable cores" from the Z3 solver to pinpoint conflicting constraints.

## Installation

1.  Ensure Python 3.8+ is installed.
2.  Install the required dependencies:

    ```bash
    pip install -e .
    ```

    Dependencies include:
    *   `lark`: For parsing context-free grammars.
    *   `z3-solver`: For formal verification.
    *   `jsonschema`: For JSON structure validation.

## Usage

### Command Line Interface

To compile and verify a contract file:

```bash
python3 -m src.cli.main <path_to_contract.json>
```

Example:

```bash
python3 -m src.cli.main contracts/valid/seq_simple.json
```

### Running Tests

The project includes a comprehensive test suite covering schema validation, compilation, and verification.

To run all tests:

```bash
python3 run_tests.py
```

## Project Structure

*   `grammar/`: Contains the Lark grammar definition (`grammar.lark`).
*   `schema/`: Contains the JSON Schema (`schema.json`).
*   `src/`: Source code for the compiler, verifier, and CLI.
    *   `compiler/`: Core logic (AST, Parser, Validator, Verifier).
    *   `cli/`: Command-line entry point.
*   `contracts/`: Example contracts (valid and invalid) used for testing.
*   `tests/`: Unit tests for individual components.

## Verification Logic

The verifier maps interaction constructs to temporal constraints:
*   **Sequence (Seq)**: $t_{end}(left) \le t_{start}(right)$. Latency constraints bound $t_{end}(right) - t_{start}(left)$.
*   **Parallel (Par)**: $t_{start}(left) = t_{start}(right)$ (if synchronized).
*   **Actions (Act)**: $t_{end} \ge t_{start}$.

If the constraints are unsatisfiable, the verifier extracts the minimal set of conflicting constraints (unsat core) to aid in debugging.
