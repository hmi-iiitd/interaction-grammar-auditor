"""
Module D: Clarification Engine

Responsibility: Generate targeted questions for missing or ambiguous contract fields.
Rule-based (not LLM) — deterministically checks obligations for null fields.

Pass conditions (from PRD):
  • Missing deadline triggers deadline question.
  • Ambiguous acknowledgment triggers modality question.
  • Missing repair behavior triggers repair question.
  • Fully specified scenario does not trigger unnecessary questions.
  • User answers update draft obligations.
"""

import logging
from typing import List

from authoring.schemas import (
    Obligation,
    ClarificationQuestion,
    ClarificationAnswer,
    ScenarioSummary,
)
from authoring.obligation_extractor import get_missing_fields

logger = logging.getLogger(__name__)


def generate_questions(summary: ScenarioSummary) -> List[ClarificationQuestion]:
    """
    Generate clarification questions for all missing/ambiguous fields
    in the obligations.

    Categories:
      - deadline_missing
      - event_modality_missing
      - repair_policy_missing
      - interruption_priority_missing
      - failure_condition_missing
      - event_mapping_ambiguous
    """
    questions: List[ClarificationQuestion] = []
    missing = get_missing_fields(summary.obligations)

    for m in missing:
        obl_id = m["obligation_id"]
        category = m["category"]
        context = m["context"]

        if category == "deadline_missing":
            questions.append(ClarificationQuestion(
                category="deadline_missing",
                question_text=(
                    f"How long should the system wait for the expected response?\n"
                    f"Context: {context}"
                ),
                suggested_options=["0.5 seconds", "1.0 seconds", "2.0 seconds", "5.0 seconds", "10.0 seconds"],
                related_obligation_id=obl_id,
                required=True,
            ))

        elif category == "repair_policy_missing":
            questions.append(ClarificationQuestion(
                category="repair_policy_missing",
                question_text=(
                    f"What should happen if the expected response is missing?\n"
                    f"Context: {context}"
                ),
                suggested_options=[
                    "Retry (specify max retries)",
                    "Fail immediately",
                    "Wait silently",
                    "Fallback behavior",
                ],
                related_obligation_id=obl_id,
                required=True,
            ))

        elif category == "event_modality_missing":
            questions.append(ClarificationQuestion(
                category="event_modality_missing",
                question_text=(
                    f"What modalities should count as a valid response?\n"
                    f"Context: {context}"
                ),
                suggested_options=[
                    "Speech (verbal yes/no)",
                    "Head nod / shake",
                    "Button press",
                    "Gaze at robot",
                ],
                related_obligation_id=obl_id,
                required=True,
            ))

    # Check for interruption obligations without priority
    for obl in summary.obligations:
        if obl.obligation_type == "conditional_sequence" and obl.condition:
            if "interrupt" in obl.condition.lower() or "interrupt" in obl.trigger.lower():
                # Check if there's a missing question about priority
                already_asked = any(
                    q.related_obligation_id == obl.obligation_id
                    for q in questions
                )
                if not already_asked and obl.deadline_seconds is None:
                    questions.append(ClarificationQuestion(
                        category="interruption_priority_missing",
                        question_text=(
                            f"How quickly should the robot respond to the interruption?\n"
                            f"Context: {obl.trigger} → {obl.expected}"
                        ),
                        suggested_options=["0.5 seconds", "1.0 seconds", "2.0 seconds"],
                        related_obligation_id=obl.obligation_id,
                        required=True,
                    ))

    # Check for repair without failure condition
    repair_sites = {obl.site for obl in summary.obligations if obl.obligation_type == "repair"}
    failure_sites = {obl.site for obl in summary.obligations if obl.obligation_type == "failure"}
    for site in repair_sites - failure_sites:
        questions.append(ClarificationQuestion(
            category="failure_condition_missing",
            question_text=(
                f"What should happen if all retries at site '{site}' are exhausted?\n"
                f"Should the interaction be marked as failed?"
            ),
            suggested_options=[
                "Mark interaction as failed",
                "Continue without acknowledgment",
                "Escalate to human operator",
            ],
            related_obligation_id="",
            required=False,
        ))

    # Add ambiguity-based questions from the summary
    for ambiguity in summary.potential_ambiguities:
        if not any(ambiguity.lower() in q.question_text.lower() for q in questions):
            questions.append(ClarificationQuestion(
                category="event_mapping_ambiguous",
                question_text=f"Clarification needed: {ambiguity}",
                suggested_options=[],
                related_obligation_id="",
                required=False,
            ))

    logger.info(f"Generated {len(questions)} clarification questions")
    return questions


def apply_answers(
    obligations: List[Obligation],
    answers: List[ClarificationAnswer],
    questions: List[ClarificationQuestion],
) -> List[Obligation]:
    """
    Apply user answers to update the obligations.

    Returns the updated list of obligations.
    """
    # Build a lookup: question_id → (question, answer)
    q_map = {q.question_id: q for q in questions}

    for ans in answers:
        q = q_map.get(ans.question_id)
        if not q:
            continue

        # Find the obligation to update
        target_obl = None
        for obl in obligations:
            if obl.obligation_id == q.related_obligation_id:
                target_obl = obl
                break

        if target_obl is None:
            continue

        if q.category == "deadline_missing" or q.category == "interruption_priority_missing":
            # Extract numeric value from answer
            deadline = _extract_number(ans.answer_text or (ans.selected_options[0] if ans.selected_options else ""))
            if deadline is not None:
                target_obl.deadline_seconds = deadline
                logger.info(f"Set deadline for {target_obl.obligation_id}: {deadline}s")

        elif q.category == "repair_policy_missing":
            answer_text = ans.answer_text or (ans.selected_options[0] if ans.selected_options else "")
            if "retry" in answer_text.lower():
                # Try to extract retry count
                count = _extract_number(answer_text)
                if count is not None:
                    target_obl.max_retries = int(count)
                else:
                    target_obl.max_retries = 2  # Default, marked as assumption

        elif q.category == "event_modality_missing":
            modalities = ans.selected_options if ans.selected_options else []
            if ans.answer_text:
                modalities.append(ans.answer_text)
            target_obl.modalities = modalities

    return obligations


def _extract_number(text: str) -> float | None:
    """Extract the first numeric value from a string."""
    import re
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        return float(match.group(1))
    return None
