# Interaction Grammar Framework

## Overview
The Interaction Grammar Framework is a comprehensive tool designed to formalize, compile, and audit Human-Robot Interaction (HRI) contracts. It provides a formal specification language to define interaction protocols, bounds, and constraints between multiple agents (e.g., humans and robots).

This framework focuses on:
1. **Structural Validation**: Ensuring interaction contracts are well-formed via JSON Schema.
2. **Grammar-Based Parsing**: Utilizing a context-free grammar to parse constraints like latency, synchronization, and retry policies.
3. **AST Compilation**: Converting parsed JSON into a typed Abstract Syntax Tree (AST) representing sequences, parallels, repairs, negations, and binds.
4. **Semantic Validation**: Enforcing logical constraints such as agent naming conventions and valid latency boundaries.
5. **Auditing**: Validating real-world execution traces (e.g., from ROS 2 bags) against formal interaction contracts.

---

## 1. Core Architecture

The system is composed of several interlocking components:

### 1.1 Compiler
The compiler (`src/compiler/`) is responsible for turning raw JSON contracts into validated AST nodes.
- **AST (`ast.py`)**: Defines nodes like `Act`, `Seq`, `Par`, `Repair`, `Neg`, and `Bind`.
- **Parser (`parser.py`)**: Traverses the JSON structure and instantiates AST nodes.
- **Constraint Parser (`constraint_parser.py`)**: Uses the Lark parsing library with `grammar.lark` to parse symbolic and numeric latency/synchronization constraints.
- **Validator (`validator.py`)**: Contains both `SchemaValidator` (using `schema.json`) and `SemanticValidator` to enforce well-formedness.

### 1.2 Auditor
The auditor (`src/audit/`) takes an compiled AST and a chronological trace of events and evaluates adherence.
- **Trace Management (`trace.py`)**: Loads, parses, and normalizes `.jsonl` trace files.
- **Event Matcher (`matcher.py`)**: Checks if a concrete trace event satisfies the requirements of an abstract `Act` node.
- **Auditing Engine (`auditor.py`)**: Traverses the AST recursively, searching the trace for matching patterns, evaluating time bounds, and generating an `AuditResult` indicating `PASS` or `FAIL`.

### 1.3 Grammar and Schema
- **`grammar.lark`**: A formal Lark grammar defining how strings like `≤2s`, `Δ(t1, t2)`, `start=≤300ms`, and `N≤2,μ≤0.2` should be parsed.
- **`schema.json`**: A JSON schema ensuring that all contracts conform to the required JSON structure before deep parsing begins.

---

## 2. Interaction Grammar Elements

### 2.1 Act (Action)
The most basic element representing an atomic action by an agent.
- `prim`: Primitive type (`σ` for start, `ρ` for end, `τ` for point/instantaneous, `α` for abstract).
- `agent`: The actor (e.g., `robot_1`, `human_1`).
- `channel`: The modality (e.g., `speech`, `manipulation`).
- `object`: (Optional) Specific target or payload (e.g., `prompt`, `ack`).

### 2.2 Seq (Sequence)
Enforces a strict chronological ordering between two interaction elements.
- `left`: The first interaction.
- `right`: The second interaction that must follow `left`.
- `latency`: (Optional) Maximum allowable time between the completion of `left` and the start of `right`.

### 2.3 Par (Parallel)
Defines interactions that occur concurrently.
- `left` & `right`: The two concurrent branches.
- `sync`: (Optional) Constraints like `start` or `end` to bound how much time can separate the two branches.

### 2.4 Repair
Defines error-handling and retry mechanics.
- `site`: A labeled point in the interaction where the repair is applicable.
- `expr`: The interaction to attempt.
- `retry`: Constraints dictating how many times to retry (`N_leq`) and under what conditions.

### 2.5 Neg (Negation/Disruption)
Specifies patterns that *must not* occur. If the inner expression is matched, the contract fails.

### 2.6 Bind
Groups multiple interactions and applies a shared policy or latency boundary across them.

---

## 3. The S3 NAO Scenario: Turn-Taking & Interruptions

### 3.1 Overview
Scenario 3 (S3) models a turn-taking interaction between a NAO robot (`robot_1`) and a human user (`human_1`). The robot asks a prompt, the human acknowledges, and the robot confirms. S3 includes rules about allowable latency and interruptions.

### 3.2 The S3 Contract (`scenario3_combined.json`)
The combined contract models a `bind` of three primary constraints:
1. **Prompt-Ack Sequence**: `robot_1` provides a prompt `α`, followed by `human_1` acknowledging `α`. Must complete within 8 seconds.
2. **Ack-Confirm Sequence**: `human_1` acknowledges `α`, followed by `robot_1` confirming `α`. Must complete within 1 second.
3. **No Interruption Rule**: A `neg` expression asserting that while the human is speaking (between `σ` and `ρ`), the robot must not issue an `interrupt` (`α`).

### 3.3 Data and Traces
The project contains several real and synthetic traces to validate S3 behavior.

- **Trace Extraction (`ig_extract_trace.py`)**: A script that reads ROS 2 `.db3` bag files and converts `/interaction/robot_event` and `/interaction/human_event` topics into chronological JSONL traces.

#### ROS 2 Bag: S3_pass_01
- Bag file stored in `data/bags/nao/S3_pass_01.db3` (or zip). Metadata in `S3_pass_01.meta.json`.
- Extracted trace: `data/traces/nao/S3_pass_01.trace.jsonl`
- Contains: Robot prompt, human speaking start/end, human ack, robot confirm.
- **Verdict**: Validated against `scenario3_combined.json`. The audit (`data/reports/nao/S3_pass_01.audit.json`) showed a latency failure because the prompt-ack sequence took 8.8 seconds, violating the <= 8s limit (or a similar limit in older contract versions).

#### Trace: s3_pass.jsonl
- A clean synthetic trace where the prompt, ack, and confirm all happen within the specified latency bounds.
- **Verdict**: PASS.

#### Trace: s3_no_confirm.jsonl
- The robot prompts, the human acknowledges, but the robot *never* confirms.
- **Verdict**: FAIL (`V_SEQ_MISSING_RIGHT`). The auditor correctly identifies that the second half of the sequence (the robot's confirmation) is missing.

#### Trace: s3_interrupt.jsonl
- The robot prompts, the human begins speaking (`σ`), the robot issues an `interrupt` object, and then the human finishes speaking (`ρ`).
- **Verdict**: FAIL (`V_NEG_VIOLATED`). The auditor matches the negated pattern (robot interrupting while human is speaking) and correctly fails the contract.

---

## 4. Auditing Process & Diagnostics

When the Auditor runs, it traverses the AST and the trace sequentially. It generates an `AuditResult` indicating `PASS` or `FAIL`.

If an interaction fails, the Auditor provides rich diagnostics:
- **`operator`**: The AST node that failed (e.g., `sequence`, `parallel`, `negation`).
- **`error_code`**: A specific identifier for the failure (e.g., `V_SEQ_LATENCY_EXCEEDED`, `V_PAR_SYNC_START`, `V_REPAIR_EXHAUSTED`).
- **`clause_path`**: JSON path indicating exactly which part of the contract failed (e.g., `$.items[1].left`).
- **`responsible_agent`**: Heuristic-based attribution of which agent likely caused the failure.
- **`budget`** & **`observed`**: Shows the defined constraint vs. the actual measured value (e.g., limit <= 3s, actual = 8.8s).
- **`witness`**: Extracted trace events that prove the success or failure of the clause.

---

## 5. Getting Started & Development

### 5.1 Installation
1. Ensure Python 3.10+ is installed.
2. Install the package locally:
   ```bash
   pip install -e .
   ```

### 5.2 Command Line Interface
- **Compiler**: Validate a contract against the schema and grammar.
  ```bash
  interaction-compiler contracts/valid/seq_simple.json
  ```
- **Auditor**: Run an audit using a contract and a trace.
  ```bash
  ig-audit --contract contracts/nao/scenario3_combined.json --trace data/traces/nao/s3_pass.jsonl
  ```

### 5.3 Testing
The framework uses `pytest` and `unittest` for rigorous validation.
```bash
python3 run_tests.py
# or
pytest interaction-grammar/tests/
```
Tests cover:
- Schema validation (`test_schema_validation.py`)
- Compiler AST generation (`test_compiler.py`)
- Semantic constraints (`test_semantic_validation.py`)
- Core Auditor logic (`test_auditor.py`, `test_auditor_phase3.py`)
- Stress testing against deep ASTs and large traces (`test_stress.py`)

## Conclusion
The Interaction Grammar Framework provides a robust, formally verified approach to defining and auditing complex, multi-agent interactions. By combining schema validation, context-free grammar parsing, and chronological trace analysis, it ensures that robots and systems behave within specified temporal and structural constraints during human interactions.

---

## 6. Extensive API Reference

### 6.1 `src.compiler.ast`
Provides dataclasses representing the AST nodes. All nodes inherit from `ASTNode`.
- `Act(prim: str, agent: Union[str, List[str]], channel: str, object: Optional[str])`
- `Seq(left: ASTNode, right: ASTNode, latency: Optional[LatencyConstraint])`
- `Par(left: ASTNode, right: ASTNode, sync: Optional[Dict[str, SyncConstraint]])`
- `Repair(site: str, expr: ASTNode, retry: Optional[RetryConstraint])`
- `Neg(expr: ASTNode, disrupt: Optional[str])`
- `Bind(items: List[ASTNode], latency: Optional[LatencyConstraint], policy: Optional[Dict])`

### 6.2 `src.compiler.parser`
The `ContractParser` class provides the `parse(data: Dict) -> ASTNode` method.
It uses dynamic dispatch (`_parse_act`, `_parse_seq`, etc.) to recursively build the AST.

### 6.3 `src.compiler.constraint_parser`
Uses `Lark` and `grammar.lark` to parse strings into constraints.
- `LatencyConstraint(value_ms: Optional[float], symbolic: Optional[str])`
- `SyncConstraint(value_ms: Optional[float], symbolic: Optional[str], type: str)`
- `RetryConstraint(n_max: int, mu_max: Optional[float])`

### 6.4 `src.audit.trace`
- `Event(t: float, prim: str, agent: str, channel: str, object: Optional[str])`
- `Trace(events: List[Event])`
  - `Trace.from_file(path: str) -> Trace`: Loads from JSONL.
  - `Trace.filter(agent: str, channel: str) -> Trace`: Returns a filtered trace.

### 6.5 `src.audit.auditor`
- `Auditor(contract: ASTNode)`
  - `audit(trace: Trace) -> AuditResult`: Executes the main auditing loop.
- `AuditResult`: Holds the verdict (`PASS`/`FAIL`) and diagnostic info (`error_code`, `observed`, etc.)

---

## 7. Developer Notes & Expansion Guide

### Adding New Node Types
To add a new interaction primitive or compositional node:
1. **Schema**: Update `schema/schema.json` with the new node structure.
2. **Grammar**: If it introduces new string formats, update `grammar/grammar.lark` and `ConstraintParser`.
3. **AST**: Add a dataclass to `src/compiler/ast.py`.
4. **Parser**: Add a `_parse_<nodename>` method to `ContractParser`.
5. **Validator**: Add a `_validate_<nodename>` method to `SemanticValidator`.
6. **Auditor**: Add a `_check_<nodename>` method to `Auditor`.

