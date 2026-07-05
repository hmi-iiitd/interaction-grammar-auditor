import json
from pathlib import Path
import yaml

def clean_metadata():
    # Load Ground Truth
    with open("interaction-grammar/dataset_nao/ground_truth.json", "r") as f:
        gt_list = json.load(f)
    gt_map = {item["scenario_id"]: item for item in gt_list}

    dataset_dir = Path("interaction-grammar/dataset_nao")

    for scenario_dir in dataset_dir.iterdir():
        if not scenario_dir.is_dir():
            continue

        meta_path = scenario_dir / "metadata.yaml"
        if not meta_path.exists():
            continue

        sid = scenario_dir.name
        if sid not in gt_map:
            print(f"Skipping {sid}, not found in ground truth")
            continue

        # Read existing metadata to preserve contract and file info
        with open(meta_path, "r") as f:
            # Use a safer loader or handle multiple identical keys
            # Since yaml.safe_load usually takes the LAST key, we'll use that
            # but we want to explicitly rebuild the file.
            try:
                current_meta = yaml.safe_load(f)
            except Exception as e:
                print(f"Error reading {meta_path}: {e}")
                continue

        gt = gt_map[sid]

        # Rebuild metadata according to PRD 4.3
        new_meta = {
            "scenario_id": sid,
            "interaction_family": current_meta.get("interaction_family", "Unknown"),
            "robot_platform": current_meta.get("robot_platform", "NAO"),
            "participant_role": current_meta.get("participant_role", "Unknown"),
            "expected_verdict": gt["expected_verdict"],
            "expected_failure_type": gt["failure_type"],
            "expected_trigger_event": gt["trigger_event"],
            "expected_failed_obligation": gt["expected_event"], # mapping expected_event to obligation
            "expected_falsification_time": gt["falsification_time"],
            "expected_agent_attribution": gt["agent_attribution"],
            "contract_id": current_meta.get("contract_id", "Unknown"),
            "contract_version": current_meta.get("contract_version", "1.0"),
            "contract_hash": current_meta.get("contract_hash", "Unknown"),
            "trace_file": current_meta.get("trace_file", "trace.jsonl"),
            "rosbag_file": current_meta.get("rosbag_file", "pending_recording"),
            "notes": current_meta.get("notes", "")
        }

        with open(meta_path, "w") as f:
            yaml.dump(new_meta, f, sort_keys=False)

        print(f"Cleaned metadata for {sid}")

if __name__ == "__main__":
    clean_metadata()
