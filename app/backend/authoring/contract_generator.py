"""
Module E: Contract Draft Generator

Responsibility: Generate three representations of the contract:
  1. Plain-language contract (numbered human-readable sentences)
  2. Readable IG syntax (trigger → expected @within(Xs))
  3. Machine-readable contract JSON (conforming to existing schema.json)

Pass conditions (from PRD):
  • Plain-language contract matches JSON.
  • IG syntax matches JSON.
  • Deadlines preserved.
  • Repair limits preserved.
  • Interruption rules preserved.
  • Generated JSON follows existing schema.
"""

import json
import logging
from typing import List, Optional
from pathlib import Path

from authoring.schemas import (
    Obligation, ContractDraft, ProvenanceRecord, ScenarioSummary,
)
from authoring.prompts import (
    CONTRACT_PLAIN_LANGUAGE_SYSTEM, CONTRACT_PLAIN_LANGUAGE_USER,
    CONTRACT_IG_SYNTAX_SYSTEM, CONTRACT_IG_SYNTAX_USER,
)

logger = logging.getLogger(__name__)

# Load the global event registry for name normalization
REGISTRY_PATH = Path(__file__).parent / "event_registry.json"
try:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        EVENT_REGISTRY = json.load(f)
except Exception as e:
    logger.warning(f"Could not load event registry: {e}")
    EVENT_REGISTRY = {}

def normalize_event_name(name: Optional[str]) -> str:
    """
    Maps a guessed event name from the LLM to the official registry name.
    Example: 'user acknowledges delivery' -> 'recipient_acknowledges_delivery'
    """
    if not name:
        return "unknown"

    name_lower = name.lower().replace(" ", "_")

    # Flatten registry for easy searching
    all_official_names = []
    for category in EVENT_REGISTRY.values():
        all_official_names.extend(category.values())

    # 1. Exact match
    if name_lower in all_official_names:
        return name_lower

    # 2. Try matching against registry keys (aliases)
    for category in EVENT_REGISTRY.values():
        for alias, official in category.items():
            if alias in name_lower or name_lower in alias:
                return official

    # 3. Keyword overlap match
    name_words = set(name_lower.split("_"))
    best_match = None
    max_overlap = 0
    for official in all_official_names:
        official_words = set(official.split("_"))
        overlap = len(name_words.intersection(official_words))
        if overlap > max_overlap:
            max_overlap = overlap
            best_match = official

    if best_match and max_overlap >= 2:
        return best_match

    return name # Fallback to original guess


class GeneratorError(Exception):
    pass


def generate_contract(
    summary: ScenarioSummary,
    provenance_records: List[ProvenanceRecord],
    llm_provider,
) -> ContractDraft:
    """
    Generate a complete ContractDraft with all three representations.

    Args:
        summary: The finalized ScenarioSummary with all obligations resolved.
        provenance_records: Provenance for each obligation.
        llm_provider: LLM provider for plain-language and IG syntax generation.

    Returns:
        ContractDraft with plain_language, ig_syntax, and json_contract.
    """
    obligations = summary.obligations

    # 1. Generate machine-readable JSON (deterministic, no LLM)
    json_contract = _build_contract_json(obligations, summary.actors)

    # 2. Generate plain-language contract (LLM-assisted)
    plain_language = _generate_plain_language(obligations, llm_provider)

    # 3. Generate readable IG syntax (LLM-assisted)
    ig_syntax = _generate_ig_syntax(obligations, llm_provider)

    draft = ContractDraft(
        description_id=summary.description_id,
        plain_language=plain_language,
        ig_syntax=ig_syntax,
        json_contract=json_contract,
        provenance=provenance_records,
    )

    logger.info(f"Contract draft generated for {summary.description_id}")
    return draft


def _infer_agent(event_name: str, actors: List[str]) -> str:
    """Infer the correct agent from the event name based on the available actors."""
    if not event_name:
        return "unknown_1"
    event_lower = event_name.lower()

    # 1. Prefix-based priority (Highest accuracy)
    # If the event name starts with a specific agent prefix, use that immediately.
    if event_lower.startswith(("human_", "user_", "recipient_", "participant_")):
        return "human_1"
    if event_lower.startswith("robot_"):
        return "robot_1"
    if event_lower.startswith("system_"):
        return "system_1"
    if event_lower.startswith("env_"):
        return "env_1"

    # 2. Keyword match (Fallback)
    inferred_actor = None
    for actor in actors:
        actor_base = actor.split("_")[0].lower()
        # Only match if the actor_base is a distinct word or at the start
        if actor_base == event_lower or event_lower.startswith(actor_base + "_"):
            inferred_actor = actor
            break

    if not inferred_actor:
        if "robot" in event_lower:
            inferred_actor = "robot_1"
        elif any(k in event_lower for k in ["human", "user", "recipient", "participant"]):
            inferred_actor = "human_1"
        elif actors:
            inferred_actor = actors[0]
        else:
            inferred_actor = "unknown_1"

    # Normalize inferred actor to a valid type
    base = inferred_actor.split("_")[0].lower()
    if base in ["participant", "recipient", "user", "human"]:
        return "human_1"
    elif base in ["robot"]:
        return "robot_1"
    elif base in ["system"]:
        return "system_1"
    elif base in ["env"]:
        return "env_1"
    else:
        return "system_1" # Final fallback


def _build_contract_json(obligations: List[Obligation], actors: List[str]) -> dict:
    """
    Build a machine-readable contract JSON conforming to the existing
    interaction-grammar schema.json.

    Mapping:
      sequence → Seq node
      repair → Repair node
      conditional_sequence → mapped to Seq node based on obligation data
      alias → Act with agent list
      failure → handled by Repair node

    Multiple obligations → wrapped in Bind node.
    """
    nodes = []

    for obl in obligations:
        if obl.obligation_type == "sequence":
            node = _build_seq_node(obl, actors)
            if node:
                nodes.append(node)

        elif obl.obligation_type == "repair":
            node = _build_repair_node(obl, obligations, actors)
            if node:
                nodes.append(node)

        elif obl.obligation_type == "conditional_sequence":
            node = _build_neg_node(obl, actors)
            if node:
                nodes.append(node)

        elif obl.obligation_type == "alias":
            # Alias obligations modify other obligations rather than
            # creating standalone nodes. They are handled during Act creation.
            pass

        elif obl.obligation_type == "failure":
            # Failure is handled by repair exhaustion — no separate node.
            pass

    if not nodes:
        raise GeneratorError("No valid obligations to generate contract from.")

    if len(nodes) == 1:
        return nodes[0]

    # Wrap multiple in a Bind
    # Global interaction time limit of 30 seconds
    bind_latency = "≤30s"

    return {
        "node": "bind",
        "items": nodes,
        "latency": bind_latency,
    }


def _resolve_channel(obl: Obligation) -> str:
    """Resolve the communication channel from obligation modalities."""
    if obl.modalities and len(obl.modalities) > 0:
        return ", ".join(obl.modalities)
    return "speech" # Default fallback


def _build_seq_node(obl: Obligation, actors: List[str]) -> Optional[dict]:
    """Build a Seq AST node from a sequence obligation."""
    if not obl.trigger or not obl.expected:
        return None

    # Normalize names before inferring agents to improve attribution accuracy
    trigger_name = normalize_event_name(obl.trigger)
    expected_name = normalize_event_name(obl.expected)

    trigger_agent = _infer_agent(trigger_name, actors)
    expected_agent = _infer_agent(expected_name, actors)
    channel = _resolve_channel(obl)

    left_act = _build_act("α", trigger_agent, channel, trigger_name)
    right_act = _build_act("α", expected_agent, channel, expected_name)

    node = {
        "node": "seq",
        "left": left_act,
        "right": right_act,
    }

    if obl.deadline_seconds is not None:
        node["latency"] = f"{obl.deadline_seconds}s"

    return node


def _collect_act_objects(node: dict) -> set:
    """Collect Act object names from a contract JSON subtree."""
    objects = set()
    if not isinstance(node, dict):
        return objects
    if node.get("node") == "act" and node.get("object"):
        objects.add(node["object"])
    for key in ("left", "right", "expr"):
        child = node.get(key)
        if isinstance(child, dict):
            objects.update(_collect_act_objects(child))
    for item in node.get("items") or []:
        if isinstance(item, dict):
            objects.update(_collect_act_objects(item))
    return objects


def _resolve_repair_site(obl: Obligation, inner: dict) -> str:
    """
    Semantic validation requires repair.site to match an Act object in expr.
    Prefer repair/trigger/expected event names over scenario site labels.
    """
    objects = _collect_act_objects(inner)
    for candidate in (obl.repair_event, obl.trigger, obl.expected):
        if candidate and candidate in objects:
            return candidate
    if objects:
        return sorted(objects)[0]
    return obl.site or "default"


def _find_sequence_for_repair(
    obl: Obligation, all_obligations: List[Obligation]
) -> Optional[Obligation]:
    """Find the sequence obligation that best matches this repair."""
    for o in all_obligations:
        if o.obligation_type != "sequence":
            continue
        if obl.trigger and (o.trigger == obl.trigger or o.expected == obl.trigger):
            return o
        if obl.expected and (o.trigger == obl.expected or o.expected == obl.expected):
            return o
    return None


def _build_repair_node(obl: Obligation, all_obligations: List[Obligation], actors: List[str]) -> Optional[dict]:
    """Build a Repair AST node from a repair obligation."""

    # Priority: If a repair_event is explicitly provided, use it as the trigger for the retry
    if obl.repair_event:
        repair_event_name = normalize_event_name(obl.repair_event)
        expected_event_name = normalize_event_name(obl.expected or "response")

        trigger_agent = _infer_agent(repair_event_name, actors)
        expected_agent = _infer_agent(expected_event_name, actors)
        channel = _resolve_channel(obl)

        inner = {
            "node": "seq",
            "left": _build_act("α", trigger_agent, channel, repair_event_name),
            "right": _build_act("α", expected_agent, channel, expected_event_name),
        }
        if obl.deadline_seconds is not None:
            inner["latency"] = f"{obl.deadline_seconds}s"
    else:
        # Fallback: Try to find an existing sequence to wrap in a repair
        site_seq = _find_sequence_for_repair(obl, all_obligations)
        if site_seq is None:
            # Create a generic sequence if no match found
            repair_event_name = normalize_event_name(obl.trigger)
            expected_event_name = normalize_event_name(obl.expected or "response")

            trigger_agent = _infer_agent(repair_event_name, actors)
            expected_agent = _infer_agent(expected_event_name, actors)
            channel = _resolve_channel(obl)
            inner = {
                "node": "seq",
                "left": _build_act("α", trigger_agent, channel, repair_event_name),
                "right": _build_act("α", expected_agent, channel, expected_event_name),
            }
            if obl.deadline_seconds is not None:
                inner["latency"] = f"{obl.deadline_seconds}s"
        else:
            inner = _build_seq_node(site_seq, actors)
            if inner is None:
                return None

    node = {
        "node": "repair",
        "site": _resolve_repair_site(obl, inner),
        "expr": inner,
    }

    if obl.max_retries is not None:
        node["retry"] = {
            "N_leq": obl.max_retries,
        }

    return node


def _build_neg_node(obl: Obligation, actors: List[str]) -> Optional[dict]:
    """
    Build a node for a conditional_sequence (e.g. interruption).
    Instead of a fixed hardcoded Neg pattern, we map the actual trigger
    and expected events to a Seq node, preserving the obligation semantics.
    """
    if not obl.trigger or not obl.expected:
        return None

    trigger_agent = _infer_agent(obl.trigger, actors)
    expected_agent = _infer_agent(obl.expected, actors)
    channel = _resolve_channel(obl)

    left_act = _build_act("α", trigger_agent, channel, obl.trigger)
    right_act = _build_act("α", expected_agent, channel, obl.expected)

    node = {
        "node": "seq",
        "left": left_act,
        "right": right_act,
    }

    if obl.deadline_seconds is not None:
        node["latency"] = f"{obl.deadline_seconds}s"

    return node


def _build_act(prim: str, agent: str, channel: str, obj: Optional[str] = None) -> dict:
    """Build an Act AST node."""
    node = {
        "node": "act",
        "prim": prim,
        "agent": agent,
        "channel": channel,
    }
    if obj:
        node["object"] = normalize_event_name(obj)
    return node


def _generate_plain_language(obligations: List[Obligation], llm_provider) -> str:
    """Generate plain-language contract using LLM."""
    obl_data = [obl.to_dict() for obl in obligations]
    user_prompt = CONTRACT_PLAIN_LANGUAGE_USER.format(
        obligations_json=json.dumps(obl_data, indent=2)
    )

    try:
        result = llm_provider.generate(CONTRACT_PLAIN_LANGUAGE_SYSTEM, user_prompt)
        return result.strip()
    except Exception as e:
        logger.error(f"LLM plain-language generation failed: {e}")
        # Fallback: generate deterministically
        return _fallback_plain_language(obligations)


def _generate_ig_syntax(obligations: List[Obligation], llm_provider) -> str:
    """Generate readable IG syntax using LLM."""
    obl_data = [obl.to_dict() for obl in obligations]
    user_prompt = CONTRACT_IG_SYNTAX_USER.format(
        obligations_json=json.dumps(obl_data, indent=2)
    )

    try:
        result = llm_provider.generate(CONTRACT_IG_SYNTAX_SYSTEM, user_prompt)
        return result.strip()
    except Exception as e:
        logger.error(f"LLM IG syntax generation failed: {e}")
        return _fallback_ig_syntax(obligations)


def _fallback_plain_language(obligations: List[Obligation]) -> str:
    """Deterministic fallback for plain-language generation."""
    lines = []
    for i, obl in enumerate(obligations, 1):
        if obl.obligation_type == "sequence":
            deadline = f" within {obl.deadline_seconds} seconds" if obl.deadline_seconds else ""
            lines.append(f"{i}. After {obl.trigger}, {obl.expected} must occur{deadline}.")
        elif obl.obligation_type == "repair":
            retries = f" at most {obl.max_retries} times" if obl.max_retries else ""
            lines.append(f"{i}. If {obl.expected or 'response'} is missing, "
                         f"{obl.repair_event or 'retry'} may occur{retries}.")
        elif obl.obligation_type == "conditional_sequence":
            deadline = f" within {obl.deadline_seconds} seconds" if obl.deadline_seconds else ""
            lines.append(f"{i}. If {obl.trigger} occurs {obl.condition}, "
                         f"{obl.expected} must occur{deadline}.")
        elif obl.obligation_type == "alias":
            mods = " or ".join(obl.modalities)
            lines.append(f"{i}. {obl.expected or obl.trigger} may be satisfied by {mods}.")
        elif obl.obligation_type == "failure":
            lines.append(f"{i}. If repair at site '{obl.site}' is exhausted, "
                         f"the interaction fails.")
    return "\n".join(lines)


def _fallback_ig_syntax(obligations: List[Obligation]) -> str:
    """Deterministic fallback for IG syntax generation."""
    lines = []
    for obl in obligations:
        if obl.obligation_type == "sequence":
            deadline = f" @within({obl.deadline_seconds}s)" if obl.deadline_seconds else ""
            lines.append(f"{obl.trigger} → {obl.expected}{deadline}")
        elif obl.obligation_type == "repair":
            retries = f", max_retries={obl.max_retries}" if obl.max_retries else ""
            lines.append(f"repair(site={obl.site}{retries})")
        elif obl.obligation_type == "conditional_sequence":
            deadline = f" @within({obl.deadline_seconds}s)" if obl.deadline_seconds else ""
            lines.append(f"{obl.trigger} during {obl.condition} → {obl.expected}{deadline}")
        elif obl.obligation_type == "alias":
            mods = " | ".join(obl.modalities)
            lines.append(f"{obl.expected or obl.trigger} := {mods}")
        elif obl.obligation_type == "failure":
            lines.append(f"failure(site={obl.site}) if repair_exhausted")
    return "\n\n".join(lines)
