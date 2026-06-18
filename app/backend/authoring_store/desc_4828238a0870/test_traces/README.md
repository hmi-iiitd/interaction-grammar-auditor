# Test traces — delivery contract (`desc_4828238a0870`)

Contract: `../versions/1.0/contract.ig.json`

## Files

| File | Expected verdict | Why |
|------|----------------|-----|
| `pass.jsonl` | **PASS** | All `bind` clauses satisfied; global span ≤120s |
| `fail_latency.jsonl` | **FAIL** | 2.5s arrive→announce exceeds 1.0s (`V_SEQ_LATENCY_EXCEEDED` on `$.items[0]`) |
| `fail_ack_latency.jsonl` | **FAIL** | 3s ack→confirm exceeds 2s (`V_SEQ_LATENCY_EXCEEDED` on `$.items[2]`) |
| `fail_interruption.jsonl` | **FAIL** | Robot announces during human speech (`V_NEG_VIOLATED` on `$.items[1]`) |
| `fail_missing_success.jsonl` | **FAIL** | No `delivery_interaction_succeeds` (`V_SEQ_MISSING_RIGHT` on `$.items[4]`) |

## Pass trace note

The auditor treats the `repair` item (`no_acknowledgement_timeout` → `robot_repeats_request`) like any other obligation: the inner sequence must match somewhere in the trace (same behavior as the medication contract pass trace). The pass trace therefore includes one timeout/repeat pair so `$.items[3]` succeeds, without violating the other clauses.

## Upload (app UI)

1. **Upload** page  
2. Contract: `../versions/1.0/contract.ig.json`  
3. Trace: one of the `.jsonl` files above  
4. Scenario id: e.g. `delivery_pass` / `delivery_fail_latency`

## CLI

```bash
cd interaction-grammar
set PYTHONPATH=.
python src/cli/audit.py --contract ../app/backend/authoring_store/desc_4828238a0870/versions/1.0/contract.ig.json --trace ../app/backend/authoring_store/desc_4828238a0870/test_traces/pass.jsonl
```

Exit code 0 = PASS, 1 = FAIL.
