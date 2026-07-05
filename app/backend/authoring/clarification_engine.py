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
import json
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
    llm_provider=None,
) -> List[Obligation]:
    """
    Apply user answers to update the obligations.
    Includes an LLM-driven step to detect logical changes to the interaction sequence.

    Returns the updated list of obligations.
    """
    # Build a lookup: question_id → question
    q_map = {q.question_id: q for q in questions}

    # 1. LLM-driven Logical Analysis
    # If the user provides answers that contradict the current sequence,
    # the LLM can suggest changes to 'trigger' and 'expected' fields.
    if llm_provider:
        obl_text = "\n".join([f"ID: {o.obligation_id} | {o.trigger} -> {o.expected}" for o in obligations])
        ans_text = "\n".join([
            f"Q: {q_map[a.question_id].question_text if a.question_id in q_map else 'Unknown'} | "
            f"A: {a.answer_text or a.selected_options}"
            for a in answers
        ])

        prompt = (
            "You are an expert in interaction grammars. You are given a set of obligations "
            "(trigger -> expected) and a set of user answers to clarification questions.\n\n"
            "Your goal is to ensure the logical sequence of events matches the user's intent. "
            "Crucially, look for answers that describe a sequence of events (e.g., 'X then Y', 'first X, then Y', 'do Y before X').\n\n"
            "If a user's answer contradicts the current order of obligations (e.g., the user says 'say sorry then stop' "
            "but the current obligations are 'stop' -> 'sorry'), you MUST propose changes to the 'trigger' and 'expected' "
            "fields to swap or reorder them.\n\n"
            "Example: If User says 'Say sorry then stop' and Current is [Obl1: stop -> sorry], "
            "you should propose updates to make it [Obl1: sorry -> stop].\n\n"
            "Return a list of proposed updates in JSON format: "
            "[{'obligation_id': '...', 'field': 'trigger', 'new_value': '...'}, ...]\n"
            "If no logical changes are needed, return an empty list [].\n\n"
            f"Current Obligations:\n{obl_text}\n\n"
            f"User Answers:\n{ans_text}"
        )

        try:
            response = llm_provider.generate(prompt)
            # Simple cleanup to find JSON array in case LLM adds markdown blocks
            cleaned_resp = response.strip()
            if cleaned_resp.startswith("```json"):
                cleaned_resp = cleaned_resp.split("```json")[1].split("```")[0].strip()
            elif cleaned_resp.startswith("```"):
                cleaned_resp = cleaned_resp.split("```")[1].split("```")[0].strip()

            updates = json.loads(cleaned_resp)
            if isinstance(updates, list):
                for up in updates:
                    oid = up.get("obligation_id")
                    field = up.get("field")
                    val = up.get("new_value")

                    target = next((o for o in obligations if o.obligation_id == oid), None)
                    if target and field in ["trigger", "expected"]:
                        setattr(target, field, val)
                        logger.info(f"LLM logical update for {oid}: {field} = {val}")
        except Exception as e:
            logger.error(f"LLM logical analysis failed: {e}")

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
