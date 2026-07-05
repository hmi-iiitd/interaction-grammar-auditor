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
import os
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
    # Load event labels vocabulary
    try:
        # Get the project root directory (3 levels up from this file: authoring -> backend -> app -> root)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        labels_path = os.path.join(base_dir, "robot_event_labels.json")

        with open(labels_path, "r", encoding="utf-8") as f:
            labels_data = json.load(f)
            # Format labels as a readable list: "label: description"
            labels_str = ""
            for category, events in labels_data.items():
                labels_str += f"\n{category.replace('_', ' ').title()}:\n"
                for label, desc in events.items():
                    labels_str += f"- {label}: {desc}\n"
    except Exception as e:
        logger.error(f"Failed to load robot_event_labels.json from {labels_path if 'labels_path' in locals() else 'unknown path'}: {e}")
        labels_str = "No event labels provided."

    system_prompt = SCENARIO_CLARIFY_SYSTEM.format(event_labels=labels_str)

    user_prompt = SCENARIO_CLARIFY_USER.format(
        description=description.description,
        title=description.scenario_title or "(not provided)",
        robot_platform=description.robot_platform or "(not specified)",
        interaction_family=description.interaction_family or "(not specified)",
    )

    raw = ""

    # Retry loop to handle occasional LLM JSON truncation or malformations
    max_retries = 3
    provider_errors = []
    for attempt in range(max_retries):
        logger.info(f"Calling LLM for scenario clarification (attempt {attempt + 1}/{max_retries})...")
        try:
            raw = llm_provider.generate(system_prompt, user_prompt, json_mode=True)
        except Exception as e:
            provider_errors.append(str(e))
            logger.warning("LLM clarification call failed on attempt %s/%s: %s", attempt + 1, max_retries, e)
            continue

        # Parse the LLM response as JSON
        parsed = _extract_json(raw)
        if parsed is not None:
            break

        logger.warning(f"LLM returned invalid JSON on attempt {attempt + 1}. Retrying...")
    else:
        provider_detail = ""
        if provider_errors:
            provider_detail = "\nProvider errors:\n" + "\n".join(provider_errors[-3:])
        raise ClarifierError(
            "The LLM did not return valid structured JSON after "
            f"{max_retries} attempts. Please retry in a moment. "
            f"Raw response preview:\n{raw[:500]}"
            f"{provider_detail}"
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
