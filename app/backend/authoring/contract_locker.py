"""
Module I: Contract Locker

Responsibility: Freeze contract before audit, assign version and hash.

Pass conditions (from PRD):
  • Lock creates version.
  • Lock creates hash.
  • Same contract produces same hash.
  • Editing locked contract creates new version.
  • Audit report includes contract hash.
  • Audit cannot run on unlocked contract.
"""

import json
import logging
from typing import Optional

from authoring.schemas import (
    ContractMetadata,
    ContractDraft,
    ProvenanceRecord,
    EventMapping,
    ValidationResult,
    compute_contract_hash,
    _now_iso,
    _new_id,
)
from authoring import scenario_store as store

logger = logging.getLogger(__name__)


class LockError(Exception):
    """Raised when a locking operation cannot proceed."""
    pass


def lock_contract(
    desc_id: str,
    draft: ContractDraft,
    validation: ValidationResult,
    provenance: list[ProvenanceRecord],
    event_mappings: list[EventMapping] | None = None,
) -> ContractMetadata:
    """
    Lock a contract for auditing.

    Pre-conditions:
      - Validation must pass (all_passed == True).
      - All provenance records should be confirmed.

    Creates:
      - A versioned copy of the contract JSON.
      - A ContractMetadata with hash, version, and lock timestamp.

    Returns:
        ContractMetadata for the locked contract.
    """
    if not validation.all_passed:
        raise LockError(
            "Cannot lock: contract validation has not passed. "
            f"Errors: {validation.errors}"
        )

    # Check provenance confirmation
    confirmed = sum(1 for p in provenance if p.confirmed_by_user)
    unresolved = sum(1 for p in provenance if not p.confirmed_by_user)

    # Check for unresolved event mappings
    if event_mappings:
        unresolved_maps = [m for m in event_mappings if not m.confirmed]
        if unresolved_maps:
            raise LockError(
                f"Cannot lock: {len(unresolved_maps)} unresolved event mapping(s). "
                f"Events: {[m.contract_event for m in unresolved_maps]}"
            )

    # Determine version
    existing_meta = _load_metadata(desc_id)
    if existing_meta and existing_meta.locked:
        # Editing a locked contract → create new version
        version = _increment_version(existing_meta.version)
        logger.info(f"Creating new version {version} (previous: {existing_meta.version})")
    else:
        version = "1.0"

    # Compute hash
    contract_hash = compute_contract_hash(draft.json_contract)

    # Build contract ID from description ID
    contract_id = desc_id.replace("desc_", "contract_")

    # Create metadata
    metadata = ContractMetadata(
        contract_id=contract_id,
        version=version,
        locked=True,
        locked_at=_now_iso(),
        contract_hash=contract_hash,
        source_description_id=desc_id,
        confirmed_assumptions=confirmed,
        unresolved_assumptions=unresolved,
    )

    # Save versioned contract
    contract_with_meta = {
        **draft.json_contract,
        "_contract_metadata": metadata.to_dict(),
    }
    store.save_version(desc_id, version, contract_with_meta)

    # Save metadata
    store.save_artifact(desc_id, "contract_metadata.json", metadata.to_dict())

    # Save provenance snapshot
    store.save_artifact(
        desc_id, f"provenance_v{version}.json",
        [p.to_dict() for p in provenance],
    )

    # Save event mappings snapshot
    if event_mappings:
        store.save_artifact(
            desc_id, f"event_mappings_v{version}.json",
            [m.to_dict() for m in event_mappings],
        )

    logger.info(
        f"Contract locked: {contract_id} v{version} "
        f"hash={contract_hash[:24]}..."
    )

    return metadata


def is_locked(desc_id: str) -> bool:
    """Check if a contract is currently locked."""
    meta = _load_metadata(desc_id)
    return meta is not None and meta.locked


def get_locked_metadata(desc_id: str) -> Optional[ContractMetadata]:
    """Get the metadata for a locked contract."""
    return _load_metadata(desc_id)


def get_locked_contract(desc_id: str) -> Optional[dict]:
    """Get the locked contract JSON for auditing."""
    meta = _load_metadata(desc_id)
    if meta is None or not meta.locked:
        return None
    return store.load_version(desc_id, meta.version)


def can_audit(desc_id: str) -> tuple[bool, str]:
    """
    Check if a contract is ready for audit.

    Returns:
        (can_audit, reason) — True if locked and ready, else False with explanation.
    """
    meta = _load_metadata(desc_id)
    if meta is None:
        return False, "No contract metadata found. Generate and lock a contract first."
    if not meta.locked:
        return False, "Contract is not locked. Lock the contract before auditing."
    if meta.unresolved_assumptions > 0:
        return False, (
            f"Contract has {meta.unresolved_assumptions} unresolved assumption(s). "
            "Confirm all assumptions before auditing."
        )
    return True, f"Contract {meta.contract_id} v{meta.version} is ready for audit."


def unlock_for_edit(desc_id: str) -> ContractMetadata:
    """
    Unlock a contract to allow editing.
    The current locked version is preserved; a new version will be created on next lock.
    """
    meta = _load_metadata(desc_id)
    if meta is None:
        raise LockError("No contract metadata found.")
    if not meta.locked:
        raise LockError("Contract is not locked.")

    # Mark as unlocked (preserving previous version info)
    meta.locked = False
    store.save_artifact(desc_id, "contract_metadata.json", meta.to_dict())

    logger.info(f"Contract unlocked for editing: {meta.contract_id}")
    return meta


# ── Internal helpers ─────────────────────────────────────────────────

def _load_metadata(desc_id: str) -> Optional[ContractMetadata]:
    """Load contract metadata from the store."""
    data = store.load_artifact(desc_id, "contract_metadata.json")
    if data is None:
        return None
    return ContractMetadata.from_dict(data)


def _increment_version(version: str) -> str:
    """Increment a version string: 1.0 → 2.0, 2.0 → 3.0, etc."""
    try:
        major = int(version.split(".")[0])
        return f"{major + 1}.0"
    except (ValueError, IndexError):
        return "2.0"
