"""
Module A: Scenario Description Store

Responsibility: Save, retrieve, and list original user scenario descriptions.
Storage: file-based under authoring_store/{desc_id}/

Pass conditions (from PRD):
  • Empty description rejected.
  • Description saved with ID.
  • Metadata saved.
  • Description can be retrieved.
  • Generated contracts link back to description ID.
"""

import json
from pathlib import Path
from typing import List, Optional
from authoring.schemas import ScenarioDescription


class StoreError(Exception):
    """Raised on storage errors."""
    pass


def _store_root() -> Path:
    root = Path(__file__).parent.parent / "authoring_store"
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_description(desc: ScenarioDescription) -> str:
    """
    Persist a scenario description.

    Validates:
      - Non-empty description text
      - Very short descriptions (< 20 chars) are flagged

    Returns:
      The description_id.
    """
    text = desc.description.strip()
    if not text:
        raise StoreError("Scenario description cannot be empty.")
    if len(text) < 20:
        raise StoreError(
            "Scenario description is too short. Please provide more detail "
            "about the intended interaction."
        )

    folder = _store_root() / desc.description_id
    folder.mkdir(parents=True, exist_ok=True)

    with open(folder / "description.json", "w") as f:
        json.dump(desc.to_dict(), f, indent=2)

    return desc.description_id


def get_description(desc_id: str) -> ScenarioDescription:
    """Load a saved description by its ID."""
    path = _store_root() / desc_id / "description.json"
    if not path.exists():
        raise StoreError(f"Description not found: {desc_id}")
    with open(path) as f:
        return ScenarioDescription.from_dict(json.load(f))


def list_descriptions() -> List[ScenarioDescription]:
    """List all saved descriptions, newest first."""
    root = _store_root()
    results = []
    for folder in sorted(root.iterdir(), reverse=True):
        desc_file = folder / "description.json"
        if desc_file.exists():
            try:
                with open(desc_file) as f:
                    results.append(ScenarioDescription.from_dict(json.load(f)))
            except Exception:
                continue
    return results


def save_artifact(desc_id: str, filename: str, data: dict) -> None:
    """Save an intermediate artifact (summary, obligations, etc.) for a description."""
    folder = _store_root() / desc_id
    if not folder.exists():
        raise StoreError(f"Description folder not found: {desc_id}")
    with open(folder / filename, "w") as f:
        json.dump(data, f, indent=2)


def load_artifact(desc_id: str, filename: str) -> Optional[dict]:
    """Load a previously saved artifact."""
    path = _store_root() / desc_id / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_version(desc_id: str, version: str, data: dict, filename: str = "contract.ig.json") -> Path:
    """Save a versioned contract artifact."""
    folder = _store_root() / desc_id / "versions" / version
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_version(desc_id: str, version: str, filename: str = "contract.ig.json") -> Optional[dict]:
    """Load a versioned contract artifact."""
    path = _store_root() / desc_id / "versions" / version / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)
