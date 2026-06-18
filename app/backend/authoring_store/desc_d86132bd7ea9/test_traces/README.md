# Test traces — patient medication contract (`desc_d86132bd7ea9`)

Contract file:

`../versions/1.0/contract.ig.json`

## Files

| File | Expected verdict | Why |
|------|------------------|-----|
| `pass.jsonl` | **PASS** | All sequences within deadlines; no forbidden interruption pattern |
| `fail_latency.jsonl` | **FAIL** | 12s gap reminder→greet exceeds 10s budget (`V_SEQ_LATENCY_EXCEEDED`) |
| `fail_interruption.jsonl` | **FAIL** | Matches negated pattern: human σ → robot greets during speech → human ρ (`V_NEG_VIOLATED`) |
| `fail_missing_confirm.jsonl` | **FAIL** | Patient responds but robot never confirms (`V_SEQ_MISSING_RIGHT`) |

## Upload (app UI)

1. **Upload** page
2. Contract: `../versions/1.0/contract.ig.json`
3. Trace: one of the `.jsonl` files above
4. Scenario id: e.g. `patient_medication_pass` or `patient_medication_fail`

## CLI

```bash
cd interaction-grammar
set PYTHONPATH=.
python src/cli/audit.py --contract ../app/backend/authoring_store/desc_d86132bd7ea9/versions/1.0/contract.ig.json --trace ../app/backend/authoring_store/desc_d86132bd7ea9/test_traces/pass.jsonl
```

Exit code 0 = PASS, 1 = FAIL.
