"""
Milestone 3 dataset exporter for locked web-authored contracts.

When a scenario is locked through the authoring UI, this module mirrors the
authoring artifacts into interaction-grammar/dataset_nao/<scenario_id>/ using
the file names required by the Phase 2 PRD.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from authoring import scenario_store as store

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent.parent
DATASET_NAO_DIR = REPO_ROOT / "interaction-grammar" / "dataset_nao"


def export_locked_contract(desc_id: str) -> dict[str, Any] | None:
    """Export a locked authoring record to dataset_nao if it maps to a scenario."""
    scenario_id = _infer_scenario_id(desc_id)
    if not scenario_id:
        return None

    src_dir = BACKEND_DIR / "authoring_store" / desc_id
    dst_dir = DATASET_NAO_DIR / scenario_id
    metadata_path = dst_dir / "metadata.yaml"
    contract_meta_path = src_dir / "contract_metadata.json"

    if not dst_dir.exists() or not metadata_path.exists() or not contract_meta_path.exists():
        return None

    contract_meta = _read_json(contract_meta_path)
    version = contract_meta.get("version", "1.0")

    _copy_if_exists(src_dir / "summary.json", dst_dir / "structured_summary.json")
    _copy_if_exists(src_dir / "validation.json", dst_dir / "validation_log.json")
    _copy_if_exists(src_dir / "event_mappings.json", dst_dir / "event_mappings.json")
    _copy_if_exists(src_dir / f"provenance_v{version}.json", dst_dir / "provenance.json")
    _copy_if_exists(src_dir / "contract_metadata.json", dst_dir / "contract_lock.json")
    _copy_if_exists(src_dir / "versions" / version / "contract.ig.json", dst_dir / "contract.ig.json")

    questions = _read_json(src_dir / "questions.json") if (src_dir / "questions.json").exists() else []
    answers = _read_json(src_dir / "answers.json") if (src_dir / "answers.json").exists() else []
    _write_json(dst_dir / "clarifications.json", {"questions": questions, "answers": answers})

    description = _read_json(src_dir / "description.json") if (src_dir / "description.json").exists() else {}
    summary = _read_json(src_dir / "summary.json") if (src_dir / "summary.json").exists() else {}
    draft = _read_json(src_dir / "draft.json") if (src_dir / "draft.json").exists() else {}
    validation = _read_json(src_dir / "validation.json") if (src_dir / "validation.json").exists() else {}
    provenance_path = src_dir / f"provenance_v{version}.json"
    provenance = _read_json(provenance_path) if provenance_path.exists() else []

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
    _upsert_hash_index(
        {
            "scenario_id": scenario_id,
            "description_id": desc_id,
            "contract_id": contract_meta.get("contract_id"),
            "contract_version": contract_meta.get("version"),
            "contract_hash": contract_meta.get("contract_hash"),
        }
    )

    return {"scenario_id": scenario_id, "dataset_dir": str(dst_dir)}


def _infer_scenario_id(desc_id: str) -> str | None:
    description = store.load_artifact(desc_id, "description.json") or {}
    candidates = [
        description.get("scenario_id", ""),
        description.get("scenario_title", ""),
        description.get("notes", ""),
        desc_id.removeprefix("desc_"),
    ]
    known_ids = _known_scenario_ids()
    for candidate in candidates:
        for scenario_id in known_ids:
            if scenario_id in candidate:
                return scenario_id
            if candidate.lower() == scenario_id.lower():
                return scenario_id
    return None


def _known_scenario_ids() -> list[str]:
    matrix_path = DATASET_NAO_DIR / "scenario_matrix.json"
    if not matrix_path.exists():
        return []
    matrix = _read_json(matrix_path)
    if not isinstance(matrix, list):
        return []
    return [str(row.get("scenario_id")) for row in matrix if isinstance(row, dict) and row.get("scenario_id")]


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
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


def _upsert_hash_index(record: dict[str, Any]) -> None:
    path = DATASET_NAO_DIR / "contract_hash_index.json"
    records = _read_json(path) if path.exists() else []
    if not isinstance(records, list):
        records = []
    records = [
        item
        for item in records
        if not (isinstance(item, dict) and item.get("scenario_id") == record["scenario_id"])
    ]
    records.append(record)
    records.sort(key=lambda item: item.get("scenario_id", ""))
    _write_json(path, records)
