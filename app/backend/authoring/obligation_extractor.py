"""
Module C: Obligation Extractor

Responsibility: Extract actors, events, obligations from a structured summary.
Uses the already-extracted obligations from the clarifier (Module B) and
enriches/validates them.

Pass conditions (from PRD):
  • Extracts actors from simple scenario.
  • Extracts request-response obligation.
  • Extracts explicit deadline.
  • Extracts max retry count.
  • Extracts interruption condition.
  • Marks missing deadline as unspecified.
  • Does NOT invent deadline silently.
"""

import logging
from typing import List

from authoring.schemas import ScenarioSummary, Obligation

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    pass


def validate_extraction(summary: ScenarioSummary) -> List[str]:
    """
    Validate the extracted obligations and return a list of issues.

    Checks:
      - Every obligation has a type
      - Every sequence obligation has trigger and expected events
      - No invented deadlines (deadlines without source sentences containing numbers)
      - Repair obligations have a site
    """
    issues = []

    for obl in summary.obligations:
        if not obl.obligation_type:
            issues.append(f"Obligation {obl.obligation_id}: missing type")

        if obl.obligation_type in ("sequence", "conditional_sequence"):
            if not obl.trigger:
                issues.append(f"Obligation {obl.obligation_id}: sequence missing trigger event")
            if not obl.expected:
                issues.append(f"Obligation {obl.obligation_id}: sequence missing expected event")

        if obl.obligation_type == "repair":
            if not obl.site:
                issues.append(f"Obligation {obl.obligation_id}: repair missing site label")

        if obl.obligation_type == "alias":
            if len(obl.modalities) < 2:
                issues.append(
                    f"Obligation {obl.obligation_id}: alias should have at least 2 modalities"
                )

        # Guard against invented deadlines
        if obl.deadline_seconds is not None and obl.source_sentence:
            # Check if the source sentence contains any number
            has_number = any(c.isdigit() for c in obl.source_sentence)
            if not has_number:
                issues.append(
                    f"Obligation {obl.obligation_id}: deadline {obl.deadline_seconds}s "
                    f"may be invented — source sentence has no numeric value. "
                    f"Setting to null."
                )
                obl.deadline_seconds = None

    return issues


def enrich_obligations(summary: ScenarioSummary) -> ScenarioSummary:
    """
    Enrich and validate obligations extracted by the clarifier.

    - Assigns site labels where missing (using trigger event name)
    - Ensures all events referenced in obligations appear in events list
    - Validates and flags issues
    """
    all_events = set(summary.events)

    for obl in summary.obligations:
        # Assign default site if missing
        if not obl.site and obl.obligation_type in ("sequence", "conditional_sequence"):
            obl.site = obl.expected.replace(" ", "_") if obl.expected else "default"

        # Collect referenced events into the events list
        for event_name in [obl.trigger, obl.expected, obl.repair_event]:
            if event_name and event_name not in all_events:
                all_events.add(event_name)
                summary.events.append(event_name)

        for mod in obl.modalities:
            if mod and mod not in all_events:
                all_events.add(mod)
                summary.events.append(mod)

    # Run validation
    issues = validate_extraction(summary)
    for issue in issues:
        logger.warning(f"Extraction issue: {issue}")
        if issue not in summary.missing_details:
            summary.missing_details.append(issue)

    return summary


def get_missing_fields(obligations: List[Obligation]) -> List[dict]:
    """
    Identify which obligations have missing required fields.

    Returns a list of dicts describing what's missing, used by the
    Clarification Engine (Module D) to generate questions.
    """
    missing = []

    for obl in obligations:
        if obl.obligation_type in ("sequence", "conditional_sequence"):
            if obl.deadline_seconds is None:
                missing.append({
                    "obligation_id": obl.obligation_id,
                    "field": "deadline_seconds",
                    "category": "deadline_missing",
                    "context": f"{obl.trigger} → {obl.expected}",
                })

        if obl.obligation_type == "repair":
            if obl.max_retries is None:
                missing.append({
                    "obligation_id": obl.obligation_id,
                    "field": "max_retries",
                    "category": "repair_policy_missing",
                    "context": f"repair at site={obl.site}",
                })

        if obl.obligation_type == "alias":
            if len(obl.modalities) < 2:
                missing.append({
                    "obligation_id": obl.obligation_id,
                    "field": "modalities",
                    "category": "event_modality_missing",
                    "context": f"alias for {obl.trigger or obl.expected}",
                })

    return missing
