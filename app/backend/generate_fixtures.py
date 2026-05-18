"""
Generate all 18 scenario fixture folders under app/dataset/.

Sources:
- 4 scenarios from existing S3 traces
- 14 new synthetic scenarios

Each scenario folder follows the PDF-expected structure:
  scenario_name/
    raw/
    traces/trace.json
    contracts/contract.ig.json
    audits/audit_report.json
    audits/counterexample.json
    metadata.yaml
"""

import json
import sys
import shutil
from pathlib import Path

# Add project roots to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "interaction-grammar"))
sys.path.insert(0, str(PROJECT_ROOT / "app" / "backend"))

from transformer.audit_mapper import transform_scenario
from src.compiler.parser import ContractParser
from src.audit.auditor import Auditor
from src.audit.trace import Trace

DATASET_DIR = PROJECT_ROOT / "app" / "dataset"
CONTRACT_PATH = PROJECT_ROOT / "interaction-grammar" / "contracts" / "nao" / "scenario3_combined.json"
CONTRACT_ID = "scenario3_combined_v1"


def load_contract():
    with open(CONTRACT_PATH) as f:
        return json.load(f)


def load_and_audit(trace_events, contract_data):
    """Run the existing auditor on a list of raw events."""
    parser = ContractParser()
    ast = parser.parse(contract_data)

    from src.audit.trace import Event, Trace as TraceObj
    events = []
    for e in trace_events:
        events.append(Event(
            t=e["t"], prim=e["prim"], agent=e["agent"],
            channel=e["channel"], object=e.get("object"),
        ))
    trace = TraceObj(events)
    auditor = Auditor(ast)
    result = auditor.audit(trace)
    return result.to_dict()


def load_jsonl(path):
    """Load a JSONL trace file into a list of dicts."""
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def write_scenario(scenario_id, files, contract_data, source_bag=None):
    """Write a scenario folder to dataset/."""
    sdir = DATASET_DIR / scenario_id
    (sdir / "raw").mkdir(parents=True, exist_ok=True)
    (sdir / "traces").mkdir(parents=True, exist_ok=True)
    (sdir / "contracts").mkdir(parents=True, exist_ok=True)
    (sdir / "audits").mkdir(parents=True, exist_ok=True)

    # trace.json
    with open(sdir / "traces" / "trace.json", "w") as f:
        json.dump(files["trace.json"], f, indent=2, ensure_ascii=False)

    # contract.ig.json
    with open(sdir / "contracts" / "contract.ig.json", "w") as f:
        json.dump(contract_data, f, indent=2, ensure_ascii=False)

    # audit_report.json
    with open(sdir / "audits" / "audit_report.json", "w") as f:
        json.dump(files["audit_report.json"], f, indent=2, ensure_ascii=False)

    # counterexample.json
    if files["counterexample.json"]:
        with open(sdir / "audits" / "counterexample.json", "w") as f:
            json.dump(files["counterexample.json"], f, indent=2, ensure_ascii=False)

    # metadata.yaml
    with open(sdir / "metadata.yaml", "w") as f:
        f.write(files["metadata.yaml"])

    # Placeholder for raw bag
    if source_bag:
        placeholder = sdir / "raw" / "scenario.bag.info"
        placeholder.write_text(f"Source: {source_bag}\n")

    verdict = files["audit_report.json"]["verdict"]
    n_viol = files["audit_report.json"]["num_violations"]
    print(f"  ✓ {scenario_id:30s} → {verdict} ({n_viol} violations)")


def make_synthetic_trace(events_spec):
    """Build a raw trace from a simple spec: list of (t, prim, agent, channel, object)."""
    base_t = 1778340000.0
    return [
        {
            "t": base_t + e[0],
            "prim": e[1],
            "agent": e[2],
            "channel": e[3],
            "object": e[4] if len(e) > 4 else None,
        }
        for e in events_spec
    ]


# ============================================================================
# Scenario Definitions
# ============================================================================

def existing_scenarios(contract_data):
    """Generate scenarios from existing S3 trace files."""
    traces_dir = PROJECT_ROOT / "data" / "traces" / "nao"

    scenarios = [
        ("success_turn_01", "s3_pass.jsonl", "s3_pass.zip"),
        ("missing_ack_03", "s3_no_confirm.jsonl", "s3_no_confirm.zip"),
        ("interruption_02", "s3_interrupt.jsonl", "s3_interrupt.zip"),
        ("latency_exceeded_01", "S3_pass_01.trace.jsonl", "S3_pass_01.bag"),
    ]

    for scenario_id, trace_file, bag_name in scenarios:
        trace_path = traces_dir / trace_file
        if not trace_path.exists():
            print(f"  ✗ Skipping {scenario_id}: {trace_path} not found")
            continue
        raw_events = load_jsonl(trace_path)
        raw_audit = load_and_audit(raw_events, contract_data)
        files = transform_scenario(
            scenario_id, CONTRACT_ID, raw_events, raw_audit,
            source_bag=bag_name,
        )
        write_scenario(scenario_id, files, contract_data, source_bag=bag_name)


def synthetic_scenarios(contract_data):
    """Generate 14 synthetic scenarios."""

    defs = [
        # --- SAT scenarios ---
        (
            "success_query_02",
            [  # User queries, robot responds, user acks, robot confirms — all within bounds
                (0.0, "α", "robot_1", "speech", "prompt"),
                (1.5, "σ", "human_1", "speech", None),
                (3.0, "ρ", "human_1", "speech", None),
                (3.5, "α", "human_1", "speech", "ack"),
                (4.0, "α", "robot_1", "speech", "confirm"),
            ],
        ),
        (
            "handover_success_01",
            [  # Smooth handover with quick ack
                (0.0, "α", "robot_1", "speech", "prompt"),
                (2.0, "σ", "human_1", "speech", None),
                (4.0, "ρ", "human_1", "speech", None),
                (4.5, "α", "human_1", "speech", "ack"),
                (5.0, "α", "robot_1", "speech", "confirm"),
            ],
        ),
        (
            "success_greet_03",
            [  # Basic greeting within tight bounds
                (0.0, "α", "robot_1", "speech", "prompt"),
                (0.8, "σ", "human_1", "speech", None),
                (1.5, "ρ", "human_1", "speech", None),
                (2.0, "α", "human_1", "speech", "ack"),
                (2.5, "α", "robot_1", "speech", "confirm"),
            ],
        ),
        # --- missing_ack scenarios ---
        (
            "missing_ack_07",
            [  # Robot asks confirmation, human never acks (longer trace)
                (0.0, "α", "robot_1", "speech", "prompt"),
                (2.0, "σ", "human_1", "speech", None),
                (5.0, "ρ", "human_1", "speech", None),
                (6.0, "α", "robot_1", "speech", "status"),
                (8.0, "α", "robot_1", "speech", "retry_prompt"),
            ],
        ),
        (
            "missing_ack_12",
            [  # Robot prompts twice, human never acks either time
                (0.0, "α", "robot_1", "speech", "prompt"),
                (3.0, "σ", "human_1", "speech", None),
                (4.0, "ρ", "human_1", "speech", None),
                (9.0, "α", "robot_1", "speech", "retry_prompt"),
                (12.0, "α", "robot_1", "speech", "give_up"),
            ],
        ),
        # --- interruption scenarios ---
        (
            "interruption_05",
            [  # User interrupted during plan execution
                (0.0, "α", "robot_1", "speech", "prompt"),
                (1.0, "σ", "human_1", "speech", None),
                (1.8, "α", "robot_1", "speech", "interrupt"),
                (3.0, "ρ", "human_1", "speech", None),
                (4.0, "α", "human_1", "speech", "ack"),
                (4.5, "α", "robot_1", "speech", "confirm"),
            ],
        ),
        (
            "interruption_08",
            [  # Robot interrupts human mid-sentence, human retries
                (0.0, "α", "robot_1", "speech", "prompt"),
                (1.5, "σ", "human_1", "speech", None),
                (2.0, "α", "robot_1", "speech", "interrupt"),
                (2.5, "ρ", "human_1", "speech", None),
                (3.0, "σ", "human_1", "speech", None),
                (4.0, "ρ", "human_1", "speech", None),
                (4.5, "α", "human_1", "speech", "ack"),
                (5.0, "α", "robot_1", "speech", "confirm"),
            ],
        ),
        # --- repair_exhausted scenarios ---
        (
            "repair_exhausted_01",
            [  # Robot fails task, retries twice, still fails
                (0.0, "α", "robot_1", "speech", "prompt"),
                (10.0, "σ", "human_1", "speech", None),
                (11.0, "ρ", "human_1", "speech", None),
                (12.0, "α", "robot_1", "speech", "retry_prompt"),
                (20.0, "σ", "human_1", "speech", None),
                (21.0, "ρ", "human_1", "speech", None),
            ],
        ),
        (
            "repair_exhausted_04",
            [  # Repair with latency failures on each retry
                (0.0, "α", "robot_1", "speech", "prompt"),
                (9.0, "σ", "human_1", "speech", None),
                (10.0, "ρ", "human_1", "speech", None),
                (11.0, "α", "robot_1", "speech", "retry"),
                (20.0, "σ", "human_1", "speech", None),
                (21.0, "ρ", "human_1", "speech", None),
            ],
        ),
        # --- latency scenarios ---
        (
            "latency_exceeded_05",
            [  # Ack→Confirm takes >1s
                (0.0, "α", "robot_1", "speech", "prompt"),
                (2.0, "σ", "human_1", "speech", None),
                (3.0, "ρ", "human_1", "speech", None),
                (3.5, "α", "human_1", "speech", "ack"),
                (6.0, "α", "robot_1", "speech", "confirm"),  # 2.5s > 1s limit
            ],
        ),
        (
            "latency_exceeded_09",
            [  # Prompt→Ack extreme delay (>8s)
                (0.0, "α", "robot_1", "speech", "prompt"),
                (5.0, "σ", "human_1", "speech", None),
                (7.0, "ρ", "human_1", "speech", None),
                (12.0, "α", "human_1", "speech", "ack"),  # 12s > 8s
                (12.5, "α", "robot_1", "speech", "confirm"),
            ],
        ),
        # --- sync / parallel violation ---
        (
            "sync_violation_01",
            [  # Parallel actions desynchronized (prompt-ack still works but too slow)
                (0.0, "α", "robot_1", "speech", "prompt"),
                (4.0, "σ", "human_1", "speech", None),
                (6.0, "ρ", "human_1", "speech", None),
                (7.5, "α", "human_1", "speech", "ack"),
                (8.0, "α", "robot_1", "speech", "confirm"),
            ],
        ),
        # --- multi violation ---
        (
            "multi_violation_01",
            [  # Both latency exceeded AND no confirm (compound failure)
                (0.0, "α", "robot_1", "speech", "prompt"),
                (5.0, "σ", "human_1", "speech", None),
                (7.0, "ρ", "human_1", "speech", None),
                (9.0, "α", "human_1", "speech", "ack"),  # 9s > 8s limit → latency
                # No confirm → missing right
            ],
        ),
        # --- long trace ---
        (
            "long_trace_01",
            [  # 15+ event trace with late violation
                (0.0, "α", "robot_1", "speech", "greeting"),
                (1.0, "σ", "human_1", "speech", None),
                (2.0, "ρ", "human_1", "speech", None),
                (3.0, "α", "robot_1", "speech", "prompt"),
                (4.0, "σ", "human_1", "speech", None),
                (5.0, "ρ", "human_1", "speech", None),
                (5.5, "α", "human_1", "speech", "ack"),
                (6.0, "α", "robot_1", "speech", "confirm"),
                (7.0, "α", "robot_1", "speech", "prompt"),  # Second prompt
                (8.0, "σ", "human_1", "speech", None),
                (9.0, "ρ", "human_1", "speech", None),
                (10.0, "α", "robot_1", "speech", "status"),
                (11.0, "σ", "human_1", "speech", None),
                (12.0, "ρ", "human_1", "speech", None),
                # No second ack → missing
            ],
        ),
    ]

    for scenario_id, events_spec in defs:
        raw_events = make_synthetic_trace(events_spec)
        raw_audit = load_and_audit(raw_events, contract_data)
        files = transform_scenario(
            scenario_id, CONTRACT_ID, raw_events, raw_audit,
            source_bag=None,
        )
        write_scenario(scenario_id, files, contract_data)


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 60)
    print("TASK5 — Generating 18 Scenario Fixtures")
    print("=" * 60)

    # Clean existing dataset
    if DATASET_DIR.exists():
        shutil.rmtree(DATASET_DIR)
    DATASET_DIR.mkdir(parents=True)

    contract_data = load_contract()
    print(f"\nContract: {CONTRACT_PATH.name}")
    print(f"Output:   {DATASET_DIR}\n")

    print("--- Existing Traces ---")
    existing_scenarios(contract_data)

    print("\n--- Synthetic Scenarios ---")
    synthetic_scenarios(contract_data)

    # Count
    scenario_dirs = [d for d in DATASET_DIR.iterdir() if d.is_dir()]
    sat = sum(1 for d in scenario_dirs
              if json.loads((d / "audits" / "audit_report.json").read_text())["verdict"] == "SAT")
    unsat = len(scenario_dirs) - sat
    print(f"\n{'=' * 60}")
    print(f"Total: {len(scenario_dirs)} scenarios ({sat} SAT, {unsat} UNSAT)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
