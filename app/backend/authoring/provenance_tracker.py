"""
Module F: Provenance Tracker

Responsibility: Track where every obligation came from.
Each obligation must have provenance linking it to the original scenario
sentence, user clarification, or confirmed default.

Pass conditions (from PRD):
  • Explicit scenario sentence linked.
  • User clarification linked.
  • Default values require confirmation.
  • Unconfirmed values block locking.
"""

import logging
from typing import List

from authoring.schemas import (
    Obligation, ProvenanceRecord, ClarificationAnswer, ClarificationQuestion,
    _now_iso,
)

logger = logging.getLogger(__name__)


def create_initial_provenance(obligations: List[Obligation]) -> List[ProvenanceRecord]:
    """
    Create provenance records from the initial extraction.

    Each obligation's source_sentence becomes its provenance.
    If the source sentence is present, it's automatically confirmed
    (it came directly from the user's description).
    """
    records = []
    for obl in obligations:
        has_source = bool(obl.source_sentence and obl.source_sentence.strip())
        records.append(ProvenanceRecord(
            obligation_id=obl.obligation_id,
            source_type="scenario_sentence" if has_source else "llm_suggestion",
            source_text=obl.source_sentence if has_source else "(LLM-inferred)",
            confirmed_by_user=has_source,  # Auto-confirmed if directly from user text
        ))
    return records


def update_provenance_from_answers(
    records: List[ProvenanceRecord],
    obligations: List[Obligation],
    answers: List[ClarificationAnswer],
    questions: List[ClarificationQuestion],
) -> List[ProvenanceRecord]:
    """
    Update provenance records based on user clarification answers.

    When a user answers a clarification question, the corresponding
    obligation's provenance is updated to show user confirmation.
    """
    q_map = {q.question_id: q for q in questions}

    for ans in answers:
        q = q_map.get(ans.question_id)
        if not q or not q.related_obligation_id:
            continue

        # Find existing provenance for this obligation
        existing = None
        for rec in records:
            if rec.obligation_id == q.related_obligation_id:
                existing = rec
                break

        answer_text = ans.answer_text or ", ".join(ans.selected_options)

        if existing:
            # Update existing record
            existing.source_type = "user_clarification"
            existing.source_text = (
                f"{existing.source_text} → User clarified: {answer_text}"
            )
            existing.confirmed_by_user = True
            existing.timestamp = _now_iso()
        else:
            # Create new record
            records.append(ProvenanceRecord(
                obligation_id=q.related_obligation_id,
                source_type="user_clarification",
                source_text=f"User answered: {answer_text}",
                confirmed_by_user=True,
            ))

    return records


def get_unconfirmed(records: List[ProvenanceRecord]) -> List[ProvenanceRecord]:
    """Return all provenance records that are NOT confirmed by the user."""
    return [r for r in records if not r.confirmed_by_user]


def all_confirmed(records: List[ProvenanceRecord]) -> bool:
    """Check if ALL provenance records are confirmed. Required for locking."""
    return all(r.confirmed_by_user for r in records)


def confirm_record(records: List[ProvenanceRecord], obligation_id: str) -> None:
    """Manually confirm a provenance record (user confirmed a default)."""
    for rec in records:
        if rec.obligation_id == obligation_id:
            rec.confirmed_by_user = True
            rec.source_type = "user_confirmed_default"
            rec.timestamp = _now_iso()
            logger.info(f"Provenance confirmed for {obligation_id}")
            return

    logger.warning(f"No provenance record found for {obligation_id}")
