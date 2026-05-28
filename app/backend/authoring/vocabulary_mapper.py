"""
Module H: Event Vocabulary Mapper

Responsibility: Map contract event names to trace event names.

Pass conditions (from PRD):
  • Exact event names auto-match.
  • Fuzzy matches suggested but require confirmation.
  • Missing required event mapping blocks audit.
  • Mapping stored in metadata.
  • Mapping used by auditor.
"""

import logging
from typing import List, Set
from difflib import SequenceMatcher

from authoring.schemas import EventMapping

logger = logging.getLogger(__name__)


def auto_map(
    contract_events: List[str],
    trace_events: List[str],
) -> List[EventMapping]:
    """
    Automatically map contract events to trace events.

    Strategy:
      1. Exact match → auto-confirmed
      2. Fuzzy match (similarity > 0.6) → suggested, requires confirmation
      3. No match → mapping_type = "missing"
    """
    trace_set: Set[str] = set(trace_events)
    trace_lower = {e.lower(): e for e in trace_events}
    mappings: List[EventMapping] = []

    for ce in contract_events:
        # 1. Exact match
        if ce in trace_set:
            mappings.append(EventMapping(
                contract_event=ce,
                trace_events=[ce],
                mapping_type="exact",
                confirmed=True,
                confirmed_by="auto",
            ))
            continue

        # 1b. Case-insensitive exact
        if ce.lower() in trace_lower:
            mappings.append(EventMapping(
                contract_event=ce,
                trace_events=[trace_lower[ce.lower()]],
                mapping_type="exact",
                confirmed=True,
                confirmed_by="auto",
            ))
            continue

        # 2. Fuzzy match
        fuzzy_candidates = _fuzzy_match(ce, trace_events, threshold=0.5)
        if fuzzy_candidates:
            mappings.append(EventMapping(
                contract_event=ce,
                trace_events=fuzzy_candidates,
                mapping_type="fuzzy",
                confirmed=False,
                confirmed_by="",
            ))
            continue

        # 3. No match
        mappings.append(EventMapping(
            contract_event=ce,
            trace_events=[],
            mapping_type="missing",
            confirmed=False,
            confirmed_by="",
        ))

    return mappings


def _fuzzy_match(
    target: str,
    candidates: List[str],
    threshold: float = 0.5,
    max_results: int = 5,
) -> List[str]:
    """Find candidates that fuzzy-match the target above the threshold."""
    scored = []
    target_lower = target.lower().replace("_", " ")

    for c in candidates:
        c_lower = c.lower().replace("_", " ")

        # SequenceMatcher ratio
        ratio = SequenceMatcher(None, target_lower, c_lower).ratio()

        # Boost if one contains the other as substring
        if target_lower in c_lower or c_lower in target_lower:
            ratio = max(ratio, 0.7)

        # Boost if they share significant tokens
        target_tokens = set(target_lower.split())
        c_tokens = set(c_lower.split())
        if target_tokens & c_tokens:
            overlap = len(target_tokens & c_tokens) / max(len(target_tokens), len(c_tokens))
            ratio = max(ratio, overlap)

        if ratio >= threshold:
            scored.append((c, ratio))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:max_results]]


def confirm_mapping(
    mappings: List[EventMapping],
    contract_event: str,
    trace_events: List[str],
) -> List[EventMapping]:
    """Confirm a specific mapping by the user."""
    for m in mappings:
        if m.contract_event == contract_event:
            m.trace_events = trace_events
            m.confirmed = True
            m.confirmed_by = "user"
            m.mapping_type = "manual" if m.mapping_type == "missing" else m.mapping_type
            logger.info(f"Mapping confirmed: {contract_event} → {trace_events}")
            break
    return mappings


def has_unresolved_mappings(mappings: List[EventMapping]) -> bool:
    """Check if any required mappings are unresolved (blocks audit)."""
    return any(not m.confirmed for m in mappings)


def get_contract_events_from_json(contract_json: dict) -> List[str]:
    """
    Extract all event names (object fields) from a contract JSON.
    Walks the AST tree recursively.
    """
    events = set()
    _walk_contract(contract_json, events)
    return sorted(events)


def _walk_contract(node: dict, events: set) -> None:
    """Recursively collect 'object' values from Act nodes."""
    if not isinstance(node, dict):
        return

    if node.get("node") == "act" and "object" in node:
        events.add(node["object"])

    for key in ("left", "right", "expr"):
        if key in node:
            _walk_contract(node[key], events)

    if "items" in node and isinstance(node["items"], list):
        for item in node["items"]:
            _walk_contract(item, events)
