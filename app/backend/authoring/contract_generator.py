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

from authoring.schemas import (
    Obligation, ContractDraft, ProvenanceRecord, ScenarioSummary,
)
from authoring.prompts import (
    CONTRACT_PLAIN_LANGUAGE_SYSTEM, CONTRACT_PLAIN_LANGUAGE_USER,
    CONTRACT_IG_SYNTAX_SYSTEM, CONTRACT_IG_SYNTAX_USER,
)

logger = logging.getLogger(__name__)


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
    json_contract = _build_contract_json(obligations)

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


def _build_contract_json(obligations: List[Obligation]) -> dict:
    """
    Build a machine-readable contract JSON conforming to the existing
    interaction-grammar schema.json.

    Mapping:
      sequence → Seq node
      repair → Repair node
      conditional_sequence → Neg(Seq(...)) node
      alias → Act with agent list
      failure → handled by Repair node

    Multiple obligations → wrapped in Bind node.
    """
    nodes = []

    for obl in obligations:
        if obl.obligation_type == "sequence":
            node = _build_seq_node(obl)
            if node:
                nodes.append(node)

        elif obl.obligation_type == "repair":
            node = _build_repair_node(obl, obligations)
            if node:
                nodes.append(node)

        elif obl.obligation_type == "conditional_sequence":
            node = _build_neg_node(obl)
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
    # Calculate total span latency: max of all deadlines * 3 for safety
    max_deadline = 0
    for obl in obligations:
        if obl.deadline_seconds is not None:
            max_deadline = max(max_deadline, obl.deadline_seconds)

    bind_latency = f"≤{int(max(max_deadline * 4, 30))}s"

    return {
        "node": "bind",
        "items": nodes,
        "latency": bind_latency,
    }


def _build_seq_node(obl: Obligation) -> Optional[dict]:
    """Build a Seq AST node from a sequence obligation."""
    if not obl.trigger or not obl.expected:
        return None

    left_act = _build_act("α", "robot_1", "speech", obl.trigger)
    right_act = _build_act("α", "human_1", "speech", obl.expected)

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


def _build_repair_node(obl: Obligation, all_obligations: List[Obligation]) -> Optional[dict]:
    """Build a Repair AST node from a repair obligation."""
    site_seq = _find_sequence_for_repair(obl, all_obligations)

    if site_seq is None:
        inner = {
            "node": "seq",
            "left": _build_act("α", "robot_1", "speech", obl.repair_event or obl.trigger),
            "right": _build_act("α", "human_1", "speech", obl.expected or "response"),
        }
    else:
        inner = _build_seq_node(site_seq)
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


def _build_neg_node(obl: Obligation) -> Optional[dict]:
    """
    Build a Neg node for a conditional_sequence (interruption rule).

    Pattern: ¬(human_start → robot_interrupt → human_end)
    Meaning: robot must NOT interrupt while human is speaking.
    """
    if not obl.trigger or not obl.expected:
        return None

    # Build the inner sequence that should NOT happen
    inner_seq = {
        "node": "seq",
        "left": _build_act("σ", "human_1", "speech"),
        "right": {
            "node": "seq",
            "left": _build_act("α", "robot_1", "speech", obl.trigger),
            "right": _build_act("ρ", "human_1", "speech"),
        },
    }

    return {
        "node": "neg",
        "expr": inner_seq,
    }


def _build_act(prim: str, agent: str, channel: str, obj: Optional[str] = None) -> dict:
    """Build an Act AST node."""
    node = {
        "node": "act",
        "prim": prim,
        "agent": agent,
        "channel": channel,
    }
    if obj:
        node["object"] = obj
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
