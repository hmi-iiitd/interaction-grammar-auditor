# Test Fixtures

This directory contains valid and invalid interaction contracts used for testing.

## Contents

- `contracts/valid/`: Interaction contracts that should pass both schema validation and semantic checks.
    - `seq_simple.json`: Simple sequence with a deadline.
    - `par_sync.json`: Parallel actions with synchronization constraints.
    - `repair_retry.json`: Repair strategy with retry policies.
    - `complex_neg_repair.json`: Nested negation within a repair site, using symbolic latency.
- `contracts/invalid/`: Interaction contracts that are expected to fail.
    - `act_missing_prim.json`: Expected failure: schema requires ["node","prim","agent","channel"] for act.
    - `bind_latency_policy.json`: Expected failure: schema has not: { required: ["latency","policy"] }.
    - `invalid_agent_type.json`: Expected failure: Semantic check fails for invalid agent type (e.g., 'alien').
    - `malformed_symbolic.json`: Expected failure: Grammar fails to parse malformed symbolic delta 'Δ(t1, )'.

## Expected Failures

Tests in `test_schema_validation.py`, `test_compiler.py`, and `test_semantic_validation.py` use these fixtures to verify that the system correctly identifies and reports errors in invalid contracts.
