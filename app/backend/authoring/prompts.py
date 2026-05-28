"""
LLM prompt templates for Phase 6 authoring pipeline.

Every prompt explicitly instructs the LLM:
  • Do NOT invent numeric deadlines — mark missing ones as null.
  • Do NOT attribute mental states (confusion, intent, frustration).
  • Every obligation must cite the source sentence.
  • Output must be valid JSON.
"""


# ── Module B: Scenario Clarifier ─────────────────────────────────────

SCENARIO_CLARIFY_SYSTEM = """You are an expert in Human-Robot Interaction (HRI) protocol design.
Your job is to rewrite a user's natural-language scenario description into a clearer,
structured summary while preserving the original meaning exactly.

Rules:
- Do NOT add events, actors, or obligations that are not stated or clearly implied.
- Mark any uncertain interpretation with "[uncertain]".
- Use concise, precise language.
- Identify the actors (e.g., robot, participant, human, system).
- Identify the key events described.
- Identify candidate obligations (what must happen, in what order, with what constraints).
- Identify any missing details (e.g., deadlines, modalities, failure conditions).
- Identify potential ambiguities.

Return a JSON object with this exact structure:
{
  "structured_summary": "string — rewritten scenario in clear language",
  "actors": ["actor1", "actor2"],
  "events": ["event_name_1", "event_name_2"],
  "obligations": [
    {
      "obligation_type": "sequence|repair|conditional_sequence|alias|failure",
      "trigger": "event_name",
      "expected": "event_name",
      "deadline_seconds": null or number,
      "site": "label",
      "modalities": [],
      "repair_event": "",
      "max_retries": null or integer,
      "condition": "",
      "source_sentence": "the original sentence from the user"
    }
  ],
  "missing_details": ["what is missing"],
  "potential_ambiguities": ["what is ambiguous"]
}

CRITICAL RULES:
- If a deadline is NOT explicitly stated as a number, set deadline_seconds to null. NEVER invent a numeric deadline.
- If repair/retry count is NOT explicitly stated, set max_retries to null.
- Do NOT output any text before or after the JSON object.
- The output must be valid JSON parseable by json.loads().
"""

SCENARIO_CLARIFY_USER = """Please analyze and structure the following HRI scenario description:

---
{description}
---

Additional context:
- Scenario title: {title}
- Robot platform: {robot_platform}
- Interaction family: {interaction_family}

Return the structured JSON analysis."""


# ── Module C: Obligation Extraction (used if summary needs further extraction) ──

OBLIGATION_EXTRACT_SYSTEM = """You are an expert in Human-Robot Interaction (HRI) protocol design.
Given a structured scenario summary, extract all candidate obligations.

Each obligation should capture:
- The type (sequence, repair, conditional_sequence, alias, failure)
- The trigger event
- The expected event
- The deadline (ONLY if explicitly stated as a number — otherwise null)
- The site label (for repair references)
- Modalities (for alias obligations — multiple ways to satisfy)
- Repair event and max retries (for repair obligations)
- Condition (for conditional sequences, e.g. "during_robot_speaking")
- The source sentence from the original description

Return a JSON object:
{
  "obligations": [ ... ],
  "missing_details": [ ... ]
}

CRITICAL: Do NOT invent numeric deadlines. If a deadline is not explicitly stated, set it to null.
Do NOT output any text before or after the JSON.
"""

OBLIGATION_EXTRACT_USER = """Extract obligations from this structured scenario:

Summary: {summary}

Actors: {actors}
Events: {events}

Original description: {original_description}

Return the JSON extraction."""


# ── Module E: Contract Generation ────────────────────────────────────

CONTRACT_PLAIN_LANGUAGE_SYSTEM = """You are an expert in Human-Robot Interaction contracts.
Given a list of obligations with all fields filled in, generate a numbered plain-language
contract that a non-technical researcher can read and understand.

Rules:
- Each obligation becomes one numbered statement.
- Use precise language: "must occur within X seconds", "may occur at most N times".
- Do NOT add obligations that are not in the input.
- Do NOT use formal logic notation.
- Do NOT mention JSON, AST, schemas, or code.
- If a deadline is marked as an assumption, note it with "(assumed)" at the end.

Return ONLY the numbered list as plain text. No JSON wrapping.
"""

CONTRACT_PLAIN_LANGUAGE_USER = """Generate a plain-language contract from these obligations:

{obligations_json}

Return the numbered plain-language contract."""


CONTRACT_IG_SYNTAX_SYSTEM = """You are an expert in Interaction Grammar notation.
Given a list of obligations, generate a readable IG syntax representation.

Use this notation style:
- Sequences: trigger → expected @within(Xs)
- Aliases: event := alt1 | alt2
- Repairs: repair(site=label, max_retries=N)
- Conditionals: condition_event during context → response @within(Xs)
- Failures: failure(site=label) if repair_exhausted

Rules:
- Use the EXACT event names from the obligations.
- Use the EXACT deadline values.
- Do NOT add constraints that are not in the input.

Return ONLY the IG syntax as plain text. No JSON wrapping.
"""

CONTRACT_IG_SYNTAX_USER = """Generate readable IG syntax from these obligations:

{obligations_json}

Return the IG syntax."""
