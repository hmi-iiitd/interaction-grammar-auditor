"""
Prepare the NAO Phase 2 experiment dataset.

This script intentionally does not generate contracts, traces, audit reports, or
counterexamples from hardcoded scenario data. Those artifacts must come from the
real workflow:

1. Scenario descriptions are defined before the experiment from the PRD.
2. Researchers author contracts in the web app and lock them before audit.
3. Researchers record NAO ROS bags and run ig_extract_trace.py manually.
4. Later audit/report scripts consume the locked contract and extracted trace.

Milestones covered here:
- M1: scenario matrix, descriptions, execution prompts, ground-truth template.
- M2: per-scenario metadata and trace/rosbag slots for manual collection.
- M3: collection/validation of authored locked contracts from authoring_store.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = WORKSPACE_ROOT.parent
DATASET_NAO_DIR = WORKSPACE_ROOT / "dataset_nao"
DEFAULT_AUTHORING_STORE = REPO_ROOT / "app" / "backend" / "authoring_store"


@dataclass(frozen=True)
class NaoScenario:
    scenario_id: str
    interaction_family: str
    participant_role: str
    description: str
    execution_prompt: str
    expected_verdict: str
    expected_failure_type: str
    expected_trigger_event: str
    expected_failed_obligation: str
    expected_event: str
    observed_or_missing_event: str
    deadline: str
    expected_falsification_time: str
    failure_site: str
    expected_agent_attribution: str
    counterexample_window: str
    notes: str


SCENARIOS: list[NaoScenario] = [
    NaoScenario(
        scenario_id="A1_delivery_success",
        interaction_family="Delivery and Acknowledgment",
        participant_role="recipient",
        description=(
            "The robot announces a package delivery. The recipient should "
            "acknowledge the delivery within 8 seconds. Once acknowledged, "
            "the robot must confirm the delivery within 1 second."
        ),
        execution_prompt=(
            "Robot announces delivery; participant acknowledges within 8 seconds; "
            "robot confirms within 1 second."
        ),
        expected_verdict="SAT",
        expected_failure_type="none",
        expected_trigger_event="robot delivery announcement",
        expected_failed_obligation="none",
        expected_event="human acknowledgment, then robot confirmation",
        observed_or_missing_event="all expected events observed on time",
        deadline="ack <= 8s; confirm <= 1s",
        expected_falsification_time="none",
        failure_site="none",
        expected_agent_attribution="none",
        counterexample_window="none",
        notes="Normal delivery: announce, acknowledge, confirm.",
    ),
    NaoScenario(
        scenario_id="A2_recipient_does_not_acknowledge",
        interaction_family="Delivery and Acknowledgment",
        participant_role="recipient",
        description=(
            "The robot announces a package delivery. The recipient should "
            "acknowledge the delivery within 8 seconds. Once acknowledged, "
            "the robot must confirm the delivery within 1 second."
        ),
        execution_prompt=(
            "Robot announces delivery; participant deliberately gives no "
            "acknowledgment before the 8 second deadline."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="missing_ack",
        expected_trigger_event="robot delivery announcement",
        expected_failed_obligation="acknowledgment",
        expected_event="human acknowledgment",
        observed_or_missing_event="human acknowledgment missing",
        deadline="8s after robot delivery announcement",
        expected_falsification_time="8s after trigger",
        failure_site="acknowledgment",
        expected_agent_attribution="human_1",
        counterexample_window="from robot announcement through acknowledgment deadline",
        notes="Recipient does not acknowledge.",
    ),
    NaoScenario(
        scenario_id="A3_recipient_acknowledges_too_late",
        interaction_family="Delivery and Acknowledgment",
        participant_role="recipient",
        description=(
            "The robot announces a package delivery. The recipient should "
            "acknowledge the delivery within 8 seconds. Once acknowledged, "
            "the robot must confirm the delivery within 1 second."
        ),
        execution_prompt=(
            "Robot announces delivery; participant acknowledges only after "
            "the 8 second acknowledgment deadline."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="late_ack",
        expected_trigger_event="robot delivery announcement",
        expected_failed_obligation="acknowledgment latency",
        expected_event="human acknowledgment within 8 seconds",
        observed_or_missing_event="human acknowledgment observed too late",
        deadline="8s after robot delivery announcement",
        expected_falsification_time="8s after trigger",
        failure_site="timing",
        expected_agent_attribution="human_1",
        counterexample_window="from robot announcement through late acknowledgment",
        notes="Recipient acknowledges after the allowed window.",
    ),
    NaoScenario(
        scenario_id="A4_robot_does_not_confirm_delivery",
        interaction_family="Delivery and Acknowledgment",
        participant_role="recipient",
        description=(
            "The robot announces a package delivery. The recipient should "
            "acknowledge the delivery within 8 seconds. Once acknowledged, "
            "the robot must confirm the delivery within 1 second."
        ),
        execution_prompt=(
            "Robot announces delivery; participant acknowledges on time; robot "
            "does not confirm within 1 second."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="missing_robot_confirm",
        expected_trigger_event="human acknowledgment",
        expected_failed_obligation="delivery confirmation",
        expected_event="robot confirmation",
        observed_or_missing_event="robot confirmation missing",
        deadline="1s after human acknowledgment",
        expected_falsification_time="1s after acknowledgment",
        failure_site="closure",
        expected_agent_attribution="robot_1",
        counterexample_window="from human acknowledgment through confirmation deadline",
        notes="Robot receives acknowledgment but does not confirm delivery.",
    ),
    NaoScenario(
        scenario_id="B1_human_interrupts_robot_stops",
        interaction_family="Interruption and Turn-Taking",
        participant_role="interrupter",
        description=(
            "The robot starts speaking. If the human interrupts by speaking, "
            "the robot must stop speaking within 1 second and acknowledge the "
            "interruption by saying sorry within 1 second."
        ),
        execution_prompt=(
            "Robot starts speaking; participant interrupts; robot stops within "
            "1 second and says sorry within 1 second."
        ),
        expected_verdict="SAT",
        expected_failure_type="none",
        expected_trigger_event="human interruption",
        expected_failed_obligation="none",
        expected_event="robot stops speaking and acknowledges interruption",
        observed_or_missing_event="all expected interruption-handling events observed",
        deadline="stop <= 1s; sorry <= 1s",
        expected_falsification_time="none",
        failure_site="none",
        expected_agent_attribution="none",
        counterexample_window="none",
        notes="Human interruption is handled correctly.",
    ),
    NaoScenario(
        scenario_id="B2_human_interrupts_robot_continues",
        interaction_family="Interruption and Turn-Taking",
        participant_role="interrupter",
        description=(
            "The robot starts speaking. If the human interrupts by speaking, "
            "the robot must stop speaking within 1 second and acknowledge the "
            "interruption by saying sorry within 1 second."
        ),
        execution_prompt=(
            "Robot starts speaking; participant interrupts; robot continues "
            "speaking beyond the 1 second stop deadline."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="interruption",
        expected_trigger_event="human interruption",
        expected_failed_obligation="robot stop-after-interruption",
        expected_event="robot speaking end",
        observed_or_missing_event="robot keeps speaking too long",
        deadline="1s after human interruption",
        expected_falsification_time="1s after human interruption",
        failure_site="interruption",
        expected_agent_attribution="robot_1",
        counterexample_window="from human interruption through late robot stop",
        notes="Robot fails to yield the floor after human interruption.",
    ),
    NaoScenario(
        scenario_id="B3_robot_interrupts_human",
        interaction_family="Interruption and Turn-Taking",
        participant_role="speaker",
        description=(
            "When the human is speaking, the robot must not interrupt. The "
            "robot may respond only after the human has finished speaking."
        ),
        execution_prompt=(
            "Participant begins speaking; robot emits an utterance before the "
            "participant has finished."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="robot_interruption",
        expected_trigger_event="human speaking start",
        expected_failed_obligation="no robot interruption while human speaks",
        expected_event="robot remains silent until human speaking end",
        observed_or_missing_event="robot speech occurs during human speech",
        deadline="during human speaking interval",
        expected_falsification_time="time of robot interruption",
        failure_site="interruption_guard",
        expected_agent_attribution="robot_1",
        counterexample_window="human speaking start through robot interruption",
        notes="Robot interrupts while the human holds the floor.",
    ),
    NaoScenario(
        scenario_id="B4_robot_stops_but_no_sorry",
        interaction_family="Interruption and Turn-Taking",
        participant_role="interrupter",
        description=(
            "The robot starts speaking. If the human interrupts by speaking, "
            "the robot must stop speaking within 1 second and acknowledge the "
            "interruption by saying sorry within 1 second."
        ),
        execution_prompt=(
            "Robot starts speaking; participant interrupts; robot stops on time "
            "but does not say sorry within 1 second."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="missing_interrupt_ack",
        expected_trigger_event="robot speaking end after interruption",
        expected_failed_obligation="interruption acknowledgment",
        expected_event="robot says sorry",
        observed_or_missing_event="sorry acknowledgment missing",
        deadline="1s after robot stops",
        expected_falsification_time="1s after robot speaking end",
        failure_site="interruption_acknowledgment",
        expected_agent_attribution="robot_1",
        counterexample_window="from interruption through sorry deadline",
        notes="Robot yields the floor but does not acknowledge the interruption.",
    ),
    NaoScenario(
        scenario_id="C1_retry_success",
        interaction_family="Repair and Timeout",
        participant_role="partner",
        description=(
            "The robot prompts the user. If the user does not respond within "
            "3 seconds, the robot should retry prompting the user. At most 1 "
            "retry is allowed. The user should acknowledge the prompt."
        ),
        execution_prompt=(
            "Robot prompts; participant does not respond before 3 seconds; "
            "robot retries once; participant acknowledges after retry."
        ),
        expected_verdict="SAT",
        expected_failure_type="none",
        expected_trigger_event="initial robot prompt",
        expected_failed_obligation="none",
        expected_event="human acknowledgment after one retry",
        observed_or_missing_event="acknowledgment observed after allowed retry",
        deadline="response <= 3s per attempt; retries <= 1",
        expected_falsification_time="none",
        failure_site="none",
        expected_agent_attribution="none",
        counterexample_window="none",
        notes="One allowed retry repairs the missing initial response.",
    ),
    NaoScenario(
        scenario_id="C2_repair_exhausted",
        interaction_family="Repair and Timeout",
        participant_role="partner",
        description=(
            "The robot prompts the user. If the user does not respond within "
            "3 seconds, the robot should retry prompting the user. At most 1 "
            "retry is allowed. The user should acknowledge the prompt."
        ),
        execution_prompt=(
            "Robot prompts; participant does not respond; robot retries once; "
            "participant still does not acknowledge."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="repair_exhausted",
        expected_trigger_event="retry robot prompt",
        expected_failed_obligation="acknowledgment after repair",
        expected_event="human acknowledgment",
        observed_or_missing_event="human acknowledgment missing after allowed retry",
        deadline="3s after retry prompt",
        expected_falsification_time="3s after retry prompt",
        failure_site="repair",
        expected_agent_attribution="human_1",
        counterexample_window="from initial prompt through retry deadline",
        notes="Allowed repair attempt is exhausted without acknowledgment.",
    ),
    NaoScenario(
        scenario_id="C3_retry_limit_exceeded",
        interaction_family="Repair and Timeout",
        participant_role="partner",
        description=(
            "The robot prompts the user. If the user does not respond within "
            "3 seconds, the robot should retry prompting the user. At most 1 "
            "retry is allowed. The user should acknowledge the prompt."
        ),
        execution_prompt=(
            "Robot prompts; participant does not respond; robot retries more "
            "than once even though only 1 retry is allowed."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="retry_limit_exceeded",
        expected_trigger_event="second retry prompt",
        expected_failed_obligation="bounded repair",
        expected_event="no more than one retry",
        observed_or_missing_event="robot performs more retries than allowed",
        deadline="retry count <= 1",
        expected_falsification_time="time of extra retry",
        failure_site="repair_policy",
        expected_agent_attribution="robot_1",
        counterexample_window="from initial prompt through extra retry",
        notes="Robot exceeds the allowed retry budget.",
    ),
    NaoScenario(
        scenario_id="C4_global_timeout",
        interaction_family="Repair and Timeout",
        participant_role="partner",
        description=(
            "The robot announces package delivery, the user acknowledges within "
            "8 seconds, and the robot confirms within 1 second. The entire "
            "interaction must complete within 5 seconds."
        ),
        execution_prompt=(
            "Robot announces delivery; participant acknowledges and robot "
            "confirms, but the whole interaction exceeds 5 seconds."
        ),
        expected_verdict="UNSAT",
        expected_failure_type="global_timeout",
        expected_trigger_event="interaction start",
        expected_failed_obligation="global duration",
        expected_event="complete interaction within 5 seconds",
        observed_or_missing_event="interaction completes after 5 seconds",
        deadline="5s from interaction start",
        expected_falsification_time="5s after interaction start",
        failure_site="global_timeout",
        expected_agent_attribution="interaction-site",
        counterexample_window="full interaction span",
        notes="Local steps succeed but total interaction duration is too long.",
    ),
]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in data.items():
        if value is None:
            rendered = "null"
        elif isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            rendered = str(value)
        else:
            text = str(value).replace("\\", "\\\\").replace('"', '\\"')
            rendered = f'"{text}"'
        lines.append(f"{key}: {rendered}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        elif value == "null":
            value = None
        elif value == "true":
            value = True
        elif value == "false":
            value = False
        data[key.strip()] = value
    return data


def _remove_tree(path: Path) -> None:
    def _make_writable_and_retry(function, target, exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
            function(target)
        except Exception:
            raise exc_info[1]

    shutil.rmtree(path, onerror=_make_writable_and_retry)


def _scenario_by_id() -> dict[str, NaoScenario]:
    return {scenario.scenario_id: scenario for scenario in SCENARIOS}


def _ground_truth_record(scenario: NaoScenario) -> dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "expected_verdict": scenario.expected_verdict,
        "failure_type": scenario.expected_failure_type,
        "trigger_event": scenario.expected_trigger_event,
        "expected_event": scenario.expected_event,
        "observed_or_missing_event": scenario.observed_or_missing_event,
        "deadline": scenario.deadline,
        "falsification_time": scenario.expected_falsification_time,
        "failure_site": scenario.failure_site,
        "agent_attribution": scenario.expected_agent_attribution,
        "counterexample_window": scenario.counterexample_window,
        "locked_before_audit": False,
        "trace_collected": False,
        "audit_completed": False,
    }


def _metadata_record(scenario: NaoScenario) -> dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "interaction_family": scenario.interaction_family,
        "robot_platform": "NAO",
        "participant_role": scenario.participant_role,
        "expected_verdict": scenario.expected_verdict,
        "expected_failure_type": scenario.expected_failure_type,
        "expected_trigger_event": scenario.expected_trigger_event,
        "expected_failed_obligation": scenario.expected_failed_obligation,
        "expected_falsification_time": scenario.expected_falsification_time,
        "expected_agent_attribution": scenario.expected_agent_attribution,
        "contract_id": "pending_authoring",
        "contract_version": "pending_authoring",
        "contract_hash": "pending_authoring",
        "trace_file": "trace.jsonl",
        "rosbag_file": "pending_recording",
        "notes": scenario.notes,
    }


def init_dataset(clean: bool) -> None:
    if clean and DATASET_NAO_DIR.exists():
        _remove_tree(DATASET_NAO_DIR)

    DATASET_NAO_DIR.mkdir(parents=True, exist_ok=True)

    scenario_matrix = []
    ground_truth = []

    for scenario in SCENARIOS:
        scenario_dir = DATASET_NAO_DIR / scenario.scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)

        (scenario_dir / "scenario_description.txt").write_text(
            scenario.description + "\n", encoding="utf-8"
        )
        (scenario_dir / "nao_execution_prompt.txt").write_text(
            scenario.execution_prompt + "\n", encoding="utf-8"
        )
        _write_yaml(scenario_dir / "metadata.yaml", _metadata_record(scenario))

        scenario_matrix.append(
            {
                "scenario_id": scenario.scenario_id,
                "interaction_family": scenario.interaction_family,
                "participant_role": scenario.participant_role,
                "expected_verdict": scenario.expected_verdict,
                "expected_failure_type": scenario.expected_failure_type,
                "description_file": f"{scenario.scenario_id}/scenario_description.txt",
                "execution_prompt_file": f"{scenario.scenario_id}/nao_execution_prompt.txt",
            }
        )
        ground_truth.append(_ground_truth_record(scenario))

    _write_json(DATASET_NAO_DIR / "scenario_matrix.json", scenario_matrix)
    _write_json(DATASET_NAO_DIR / "ground_truth.json", ground_truth)

    print(f"Initialized {len(SCENARIOS)} NAO scenarios in {DATASET_NAO_DIR}")
    print("Next: author each scenario in the web app and lock the contract.")


def _load_authoring_mapping(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "scenarios" in data:
        data = data["scenarios"]
    if not isinstance(data, dict):
        raise ValueError("Authoring map must be an object: {scenario_id: description_id}")
    return {str(k): str(v) for k, v in data.items()}


def _copy_if_exists(src: Path, dst: Path, required: bool, errors: list[str]) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    if required:
        errors.append(f"Missing required authoring artifact: {src}")


def _export_authoring_to_dataset(
    scenario_id: str,
    desc_id: str,
    authoring_store: Path,
    errors: list[str],
) -> dict[str, Any] | None:
    scenario = _scenario_by_id().get(scenario_id)
    if scenario is None:
        errors.append(f"Unknown scenario_id in authoring export: {scenario_id}")
        return None

    src_dir = authoring_store / desc_id
    dst_dir = DATASET_NAO_DIR / scenario_id
    metadata_path = dst_dir / "metadata.yaml"

    if not src_dir.exists():
        errors.append(f"Authoring directory not found: {src_dir}")
        return None
    if not metadata_path.exists():
        errors.append(f"Scenario folder not initialized: {dst_dir}")
        return None

    contract_meta_path = src_dir / "contract_metadata.json"
    if not contract_meta_path.exists():
        errors.append(f"Contract is not locked for {scenario_id}: {contract_meta_path}")
        return None

    contract_meta = _read_json(contract_meta_path)
    version = contract_meta.get("version", "1.0")
    locked_contract = src_dir / "versions" / version / "contract.ig.json"

    _copy_if_exists(src_dir / "summary.json", dst_dir / "structured_summary.json", True, errors)

    questions = _read_json(src_dir / "questions.json") if (src_dir / "questions.json").exists() else []
    answers = _read_json(src_dir / "answers.json") if (src_dir / "answers.json").exists() else []
    _write_json(dst_dir / "clarifications.json", {"questions": questions, "answers": answers})

    _copy_if_exists(locked_contract, dst_dir / "contract.ig.json", True, errors)
    _copy_if_exists(contract_meta_path, dst_dir / "contract_lock.json", True, errors)
    _copy_if_exists(src_dir / "validation.json", dst_dir / "validation_log.json", True, errors)
    _copy_if_exists(src_dir / "event_mappings.json", dst_dir / "event_mappings.json", False, errors)
    _copy_if_exists(src_dir / f"provenance_v{version}.json", dst_dir / "provenance.json", False, errors)

    description = _read_json(src_dir / "description.json") if (src_dir / "description.json").exists() else {}
    summary = _read_json(src_dir / "summary.json") if (src_dir / "summary.json").exists() else {}
    draft = _read_json(src_dir / "draft.json") if (src_dir / "draft.json").exists() else {}
    validation = _read_json(src_dir / "validation.json") if (src_dir / "validation.json").exists() else {}
    provenance = (
        _read_json(src_dir / f"provenance_v{version}.json")
        if (src_dir / f"provenance_v{version}.json").exists()
        else _read_json(src_dir / "provenance.json")
        if (src_dir / "provenance.json").exists()
        else []
    )
    _write_json(
        dst_dir / "authoring_log.json",
        {
            "scenario_id": scenario_id,
            "description_id": desc_id,
            "original_natural_language_description": description.get("description", ""),
            "structured_system_interpretation": summary,
            "clarification_questions": questions,
            "user_answers": answers,
            "plain_language_contract": draft.get("plain_language", ""),
            "readable_grammar_notation": draft.get("ig_syntax", ""),
            "contract_json": draft.get("json_contract", {}),
            "provenance": provenance,
            "validation_output": validation,
            "lock_hash": contract_meta.get("contract_hash", ""),
        },
    )

    metadata = _read_simple_yaml(metadata_path)
    metadata.update(
        {
            "contract_id": contract_meta.get("contract_id", "missing"),
            "contract_version": contract_meta.get("version", "missing"),
            "contract_hash": contract_meta.get("contract_hash", "missing"),
        }
    )
    _write_yaml(metadata_path, metadata)

    return {
        "scenario_id": scenario_id,
        "description_id": desc_id,
        "contract_id": contract_meta.get("contract_id"),
        "contract_version": contract_meta.get("version"),
        "contract_hash": contract_meta.get("contract_hash"),
    }


def collect_authoring(authoring_map: Path, authoring_store: Path) -> None:
    mapping = _load_authoring_mapping(authoring_map)
    scenarios = _scenario_by_id()
    errors: list[str] = []
    hash_index: list[dict[str, Any]] = []

    for scenario_id, desc_id in mapping.items():
        if scenario_id not in scenarios:
            errors.append(f"Unknown scenario_id in authoring map: {scenario_id}")
            continue
        record = _export_authoring_to_dataset(scenario_id, desc_id, authoring_store, errors)
        if record:
            hash_index.append(record)

    _write_json(DATASET_NAO_DIR / "contract_hash_index.json", hash_index)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Collected locked contracts for {len(hash_index)} scenario(s).")


def _update_ground_truth_lock_flags() -> None:
    path = DATASET_NAO_DIR / "ground_truth.json"
    if not path.exists():
        return
    records = _read_json(path)
    if not isinstance(records, list):
        return
    for record in records:
        if isinstance(record, dict):
            record["locked_before_audit"] = True
    _write_json(path, records)


def validate_milestones() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    authoring_warnings: list[str] = []
    post_recording_warnings: list[str] = []

    if not DATASET_NAO_DIR.exists():
        errors.append(f"Dataset directory does not exist: {DATASET_NAO_DIR}")
    else:
        for scenario in SCENARIOS:
            scenario_dir = DATASET_NAO_DIR / scenario.scenario_id
            if not scenario_dir.exists():
                errors.append(f"Missing scenario folder: {scenario.scenario_id}")
                continue

            for rel in ["scenario_description.txt", "nao_execution_prompt.txt", "metadata.yaml"]:
                if not (scenario_dir / rel).exists():
                    errors.append(f"{scenario.scenario_id}: missing {rel}")

            for rel in ["structured_summary.json", "clarifications.json", "contract.ig.json", "contract_lock.json"]:
                if not (scenario_dir / rel).exists():
                    authoring_warnings.append(f"{scenario.scenario_id}: authoring artifact pending: {rel}")

            for rel in ["trace.jsonl", "audit_report.json", "report.md", "report.json"]:
                if not (scenario_dir / rel).exists():
                    post_recording_warnings.append(f"{scenario.scenario_id}: post-recording artifact pending: {rel}")

    for rel in ["scenario_matrix.json", "ground_truth.json"]:
        if not (DATASET_NAO_DIR / rel).exists():
            errors.append(f"Missing dataset-level file: {rel}")

    warnings = authoring_warnings + post_recording_warnings
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        raise SystemExit(1)

    print("Milestone 1 scaffold is present.")
    if authoring_warnings:
        print("Milestone 3 authoring/locking artifacts are incomplete.")
    else:
        print("Milestone 3 authoring/locking artifacts are complete.")
    if post_recording_warnings:
        print("Post-recording artifacts are pending by design until Milestone 4.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare NAO Phase 2 dataset artifacts.")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="Create the pre-experiment NAO dataset scaffold.")
    init.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete the existing dataset_nao directory before initializing.",
    )

    collect = sub.add_parser(
        "collect-authoring",
        help="Copy locked web-app authoring artifacts into dataset_nao.",
    )
    collect.add_argument(
        "--map",
        required=True,
        type=Path,
        help="JSON map of scenario_id to web-app description_id.",
    )
    collect.add_argument(
        "--authoring-store",
        type=Path,
        default=DEFAULT_AUTHORING_STORE,
        help="Path to app/backend/authoring_store.",
    )

    sub.add_parser("validate", help="Validate milestone scaffold/completeness.")

    args = parser.parse_args()
    command = args.command or "init"

    if command == "init":
        init_dataset(clean=not args.no_clean)
    elif command == "collect-authoring":
        collect_authoring(args.map, args.authoring_store)
    elif command == "validate":
        validate_milestones()
    else:
        parser.print_help()
        raise SystemExit(2)


if __name__ == "__main__":
    main()
