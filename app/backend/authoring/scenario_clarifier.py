"""
Module B: Scenario Clarifier

Responsibility: Use LLM to rewrite the raw scenario into a clearer
structured summary with actors, events, obligations, and missing details.

Pass conditions (from PRD):
  • Preserves original meaning.
  • Does not add unconfirmed events.
  • Marks uncertain interpretations.
  • Produces concise structured summary.
  • Allows user editing.
"""

import json
import logging
from typing import Optional

from authoring.schemas import ScenarioDescription, ScenarioSummary, Obligation
from authoring.prompts import SCENARIO_CLARIFY_SYSTEM, SCENARIO_CLARIFY_USER

logger = logging.getLogger(__name__)


class ClarifierError(Exception):
    pass


def clarify_scenario(
    description: ScenarioDescription,
    llm_provider,
) -> ScenarioSummary:
    """
    Use the LLM to produce a structured scenario summary.

    Args:
        description: The raw user scenario.
        llm_provider: An LLM provider with a .generate(system, user) method.

    Returns:
        ScenarioSummary with actors, events, obligations, and missing details.
    """
    user_prompt = SCENARIO_CLARIFY_USER.format(
        description=description.description,
        title=description.scenario_title or "(not provided)",
        robot_platform=description.robot_platform or "(not specified)",
        interaction_family=description.interaction_family or "(not specified)",
    )

    logger.info("Calling LLM for scenario clarification...")
    raw = llm_provider.generate(SCENARIO_CLARIFY_SYSTEM, user_prompt)

    # Parse the LLM response as JSON
    parsed = _extract_json(raw)
    if parsed is None:
        raise ClarifierError(
            f"LLM did not return valid JSON. Raw response:\n{raw[:500]}"
        )

    # Build obligations from the parsed data
    obligations = []
    for obl_data in parsed.get("obligations", []):
        obligations.append(Obligation(
            obligation_type=obl_data.get("obligation_type", ""),
            trigger=obl_data.get("trigger", ""),
            expected=obl_data.get("expected", ""),
            deadline_seconds=obl_data.get("deadline_seconds"),
            site=obl_data.get("site", ""),
            modalities=obl_data.get("modalities", []),
            repair_event=obl_data.get("repair_event", ""),
            max_retries=obl_data.get("max_retries"),
            condition=obl_data.get("condition", ""),
            source_sentence=obl_data.get("source_sentence", ""),
        ))

    summary = ScenarioSummary(
        description_id=description.description_id,
        structured_summary=parsed.get("structured_summary", ""),
        actors=parsed.get("actors", []),
        events=parsed.get("events", []),
        obligations=obligations,
        missing_details=parsed.get("missing_details", []),
        potential_ambiguities=parsed.get("potential_ambiguities", []),
    )

    logger.info(
        f"Clarification complete: {len(summary.actors)} actors, "
        f"{len(summary.events)} events, {len(summary.obligations)} obligations"
    )
    return summary


def _extract_json(text: str) -> Optional[dict]:
    """
    Extract a JSON object from LLM output, handling markdown code fences.
    """
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    for fence in ["```json", "```"]:
        if fence in text:
            start = text.index(fence) + len(fence)
            end = text.index("```", start) if "```" in text[start:] else len(text)
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    # Try finding first { and last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    return None
