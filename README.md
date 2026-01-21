# Interaction Contract Compiler

This project implements a compiler for Interaction Contracts, a formal specification language for human-robot interaction (HRI). It focuses on structural validation, parsing, and semantic checks.

## Features

*   **Schema Validation**: Validates input JSON contracts against a rigorous JSON Schema to ensure structural correctness.
*   **Grammar-Based Parsing**: Utilizes the Lark parsing library to parse complex constraint strings (e.g., latency, synchronization, retry policies) defined in the authoritative grammar.
*   **Abstract Syntax Tree (AST)**: Compiles the raw JSON into a typed AST representing the interaction logic (Sequences, Parallels, Repairs, Actions).
*   **Semantic Validation**: Performs checks beyond schema validation to ensure logical consistency of the interaction structure.
*   **Error Reporting**: Provides detailed error messages, including specific schema violations and semantic errors.

## Installation

1.  Ensure Python 3.8+ is installed.
2.  Install the required dependencies:

    ```bash
    pip install -e .
    ```

    Dependencies include:
    *   `lark`: For parsing context-free grammars.
    *   `jsonschema`: For JSON structure validation.

## Usage

### Command Line Interface

To compile and validate a contract file:

```bash
python3 -m src.cli.main <path_to_contract.json>
```

Example:

```bash
python3 -m src.cli.main contracts/valid/seq_simple.json
```

### Running Tests

The project includes a test suite covering schema validation and compilation.

To run all tests:

```bash
pytest
```

## Project Structure

*   `grammar/`: Contains the Lark grammar definition (`grammar.lark`).
*   `schema/`: Contains the JSON Schema (`schema.json`).
*   `contracts/`: Example contracts (valid and invalid) used for testing.
*   `src/`: Source code for the compiler and CLI.
    *   `compiler/`: Core logic (AST, Parser, Validator).
    *   `cli/`: Command-line entry point.
*   `tests/`: Unit tests for individual components.
    *   `fixtures/`: JSON files for testing with a README explaining expected failures.
