"""
Pydantic-style data schemas for Phase 6 authoring pipeline.

All data structures used across Modules A–I are defined here as
dataclasses for lightweight serialisation (no hard pydantic dependency).
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json, hashlib, uuid


# ── helpers ──────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    short = uuid.uuid4().hex[:12]
    return f"{prefix}{short}" if prefix else short


# ── Module A: Scenario Description ───────────────────────────────────

@dataclass
class ScenarioDescription:
    """Raw natural-language scenario input from the user."""
    description: str
    scenario_id: str = ""
    scenario_title: str = ""
    robot_platform: str = ""
    interaction_family: str = ""
    participant_role: str = ""
    notes: str = ""
    description_id: str = field(default_factory=lambda: _new_id("desc_"))
    created_at: str = field(default_factory=_now_iso)
    created_by: str = "user"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScenarioDescription":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Module B / C: Structured Scenario & Obligations ──────────────────

@dataclass
class Obligation:
    """A single candidate obligation extracted from the scenario."""
    obligation_id: str = field(default_factory=lambda: _new_id("obl_"))
    obligation_type: str = ""          # sequence | repair | conditional_sequence | alias | failure
    trigger: str = ""                  # event name
    expected: str = ""                 # event name
    deadline_seconds: Optional[float] = None   # None = unspecified
    site: str = ""                     # repair site label
    modalities: List[str] = field(default_factory=list)  # alias alternatives
    repair_event: str = ""             # event for retry
    max_retries: Optional[int] = None
    condition: str = ""                # e.g. "during_robot_speaking"
    source_sentence: str = ""          # original text that yielded this

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Obligation":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ScenarioSummary:
    """Structured interpretation produced by the Scenario Clarifier."""
    description_id: str = ""
    structured_summary: str = ""
    actors: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    obligations: List[Obligation] = field(default_factory=list)
    missing_details: List[str] = field(default_factory=list)
    potential_ambiguities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScenarioSummary":
        obls = [Obligation.from_dict(o) if isinstance(o, dict) else o
                for o in d.get("obligations", [])]
        return cls(
            description_id=d.get("description_id", ""),
            structured_summary=d.get("structured_summary", ""),
            actors=d.get("actors", []),
            events=d.get("events", []),
            obligations=obls,
            missing_details=d.get("missing_details", []),
            potential_ambiguities=d.get("potential_ambiguities", []),
        )


# ── Module D: Clarification ─────────────────────────────────────────

@dataclass
class ClarificationQuestion:
    """A question the system needs answered before generating the contract."""
    question_id: str = field(default_factory=lambda: _new_id("q_"))
    category: str = ""       # deadline_missing | event_modality_missing | repair_policy_missing | …
    question_text: str = ""
    suggested_options: List[str] = field(default_factory=list)
    related_obligation_id: str = ""
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClarificationQuestion":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ClarificationAnswer:
    """A user's response to a clarification question."""
    question_id: str = ""
    answer_text: str = ""
    selected_options: List[str] = field(default_factory=list)
    answered_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClarificationAnswer":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Module F: Provenance ─────────────────────────────────────────────

@dataclass
class ProvenanceRecord:
    """Tracks the origin of a single obligation."""
    obligation_id: str = ""
    source_type: str = ""     # scenario_sentence | user_clarification | user_confirmed_default | llm_suggestion
    source_text: str = ""
    confirmed_by_user: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProvenanceRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Module E: Contract Draft ─────────────────────────────────────────

@dataclass
class ContractDraft:
    """Three representations of the generated contract."""
    description_id: str = ""
    plain_language: str = ""
    ig_syntax: str = ""
    json_contract: Dict[str, Any] = field(default_factory=dict)
    provenance: List[ProvenanceRecord] = field(default_factory=list)
    generated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContractDraft":
        provs = [ProvenanceRecord.from_dict(p) if isinstance(p, dict) else p
                 for p in d.get("provenance", [])]
        return cls(
            description_id=d.get("description_id", ""),
            plain_language=d.get("plain_language", ""),
            ig_syntax=d.get("ig_syntax", ""),
            json_contract=d.get("json_contract", {}),
            provenance=provs,
            generated_at=d.get("generated_at", ""),
        )


# ── Module H: Event Vocabulary Mapping ───────────────────────────────

@dataclass
class EventMapping:
    """Maps one contract event name to trace event name(s)."""
    contract_event: str = ""
    trace_events: List[str] = field(default_factory=list)
    mapping_type: str = ""    # exact | fuzzy | manual | missing
    confirmed: bool = False
    confirmed_by: str = ""    # user | auto

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EventMapping":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Module I: Contract Metadata & Locking ────────────────────────────

@dataclass
class ContractMetadata:
    """Metadata envelope wrapping a locked contract."""
    contract_id: str = ""
    version: str = "1.0"
    locked: bool = False
    locked_at: Optional[str] = None
    contract_hash: str = ""
    source_description_id: str = ""
    confirmed_assumptions: int = 0
    unresolved_assumptions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContractMetadata":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Module G: Validation Result ──────────────────────────────────────

@dataclass
class ValidationResult:
    """Structured result from running all validators."""
    schema_valid: bool = False
    semantic_valid: bool = False
    repair_sites_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return self.schema_valid and self.semantic_valid and self.repair_sites_valid

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["all_passed"] = self.all_passed
        return d


# ── Utility: canonical hash ──────────────────────────────────────────

def compute_contract_hash(contract_json: Dict[str, Any]) -> str:
    """Deterministic SHA-256 of canonical JSON."""
    canonical = json.dumps(contract_json, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
