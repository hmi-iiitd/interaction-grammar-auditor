"""
Authoring router — Phase 6 natural-language contract authoring pipeline.

Endpoints map to the spec Steps 1–7:
  /describe          → Step 1: Save scenario description
  /clarify/{id}      → Step 2: LLM clarification + obligation extraction
  /questions/{id}    → Step 3: Clarification wizard
  /answers/{id}      → Step 3: Submit answers
  /generate/{id}     → Step 4: Generate contract draft
  /validate/{id}     → Step 5: Validate contract
  /map-events/{id}   → Step 6: Event vocabulary mapping
  /lock/{id}         → Step 7: Lock contract for audit
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Ensure authoring package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from llm.nim import NIMProvider

from authoring.schemas import (
    ScenarioDescription,
    ScenarioSummary,
    Obligation,
    ClarificationQuestion,
    ClarificationAnswer,
    ContractDraft,
    ProvenanceRecord,
    EventMapping,
    ValidationResult,
    ContractMetadata,
)
from authoring import scenario_store as store
from authoring.scenario_clarifier import clarify_scenario
from authoring.obligation_extractor import enrich_obligations, get_missing_fields
from authoring.clarification_engine import generate_questions, apply_answers
from authoring.contract_generator import generate_contract
from authoring.provenance_tracker import (
    create_initial_provenance,
    update_provenance_from_answers,
    get_unconfirmed,
)
from authoring.contract_validator import validate_contract
from authoring.vocabulary_mapper import (
    auto_map,
    confirm_mapping,
    has_unresolved_mappings,
    get_contract_events_from_json,
)
from authoring.contract_locker import (
    lock_contract as do_lock,
    is_locked,
    get_locked_metadata,
    get_locked_contract,
    can_audit,
    LockError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic request/response models ────────────────────────────────

class DescribeRequest(BaseModel):
    description: str
    scenario_title: str = ""
    robot_platform: str = ""
    interaction_family: str = ""
    participant_role: str = ""
    notes: str = ""


class DescribeResponse(BaseModel):
    description_id: str
    status: str = "saved"


class SummaryUpdateRequest(BaseModel):
    structured_summary: str = ""
    actors: List[str] = []
    events: List[str] = []
    obligations: List[dict] = []
    missing_details: List[str] = []
    potential_ambiguities: List[str] = []


class AnswerItem(BaseModel):
    question_id: str
    answer_text: str = ""
    selected_options: List[str] = []


class AnswersRequest(BaseModel):
    answers: List[AnswerItem]


class MapEventsRequest(BaseModel):
    trace_events: List[str] = []


class ConfirmMappingRequest(BaseModel):
    contract_event: str
    trace_events: List[str]


class ProvenanceConfirmRequest(BaseModel):
    obligation_id: str


# ── LLM provider singleton ──────────────────────────────────────────

_llm_provider = None


def _get_llm():
    global _llm_provider
    if _llm_provider is None:
        settings = get_settings()
        keys = [settings.nvidia_nim_api_key, settings.nvidia_nim_api_key_2]
        _llm_provider = NIMProvider(
            api_keys=keys,
            model=settings.llm_model,
            base_url=settings.nvidia_nim_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            fallback_model=settings.llm_fallback_model,
        )
    return _llm_provider


# ── Step 1: Describe Scenario ───────────────────────────────────────

@router.post("/describe", response_model=DescribeResponse)
def describe_scenario(req: DescribeRequest):
    """Save a new natural-language scenario description."""
    desc = ScenarioDescription(
        description=req.description,
        scenario_title=req.scenario_title,
        robot_platform=req.robot_platform,
        interaction_family=req.interaction_family,
        participant_role=req.participant_role,
        notes=req.notes,
    )
    try:
        desc_id = store.save_description(desc)
    except store.StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return DescribeResponse(description_id=desc_id)


@router.get("/descriptions")
def list_descriptions():
    """List all saved scenario descriptions."""
    descs = store.list_descriptions()
    return {
        "descriptions": [d.to_dict() for d in descs],
        "total": len(descs),
    }


@router.get("/description/{desc_id}")
def get_description(desc_id: str):
    """Get a single scenario description."""
    try:
        desc = store.get_description(desc_id)
    except store.StoreError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return desc.to_dict()


# ── Step 2: Clarify & Extract ───────────────────────────────────────

@router.post("/clarify/{desc_id}")
def clarify(desc_id: str):
    """
    Run LLM clarification on a scenario description.
    Produces a structured summary with actors, events, and obligations.
    """
    try:
        desc = store.get_description(desc_id)
    except store.StoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        summary = clarify_scenario(desc, _get_llm())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clarification failed: {e}")

    # Enrich/validate obligations
    summary = enrich_obligations(summary)

    # Create initial provenance
    provenance = create_initial_provenance(summary.obligations)

    # Save artifacts
    store.save_artifact(desc_id, "summary.json", summary.to_dict())
    store.save_artifact(
        desc_id, "provenance.json", [p.to_dict() for p in provenance]
    )

    return {
        "summary": summary.to_dict(),
        "provenance": [p.to_dict() for p in provenance],
    }


@router.get("/summary/{desc_id}")
def get_summary(desc_id: str):
    """Get the stored structured summary."""
    data = store.load_artifact(desc_id, "summary.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Summary not found. Run clarify first.")
    provenance = store.load_artifact(desc_id, "provenance.json") or []
    return {"summary": data, "provenance": provenance}


@router.put("/summary/{desc_id}")
def update_summary(desc_id: str, req: SummaryUpdateRequest):
    """Update the structured summary (user edits)."""
    existing = store.load_artifact(desc_id, "summary.json")
    if existing is None:
        raise HTTPException(status_code=404, detail="Summary not found. Run clarify first.")

    # Merge updates
    if req.structured_summary:
        existing["structured_summary"] = req.structured_summary
    if req.actors:
        existing["actors"] = req.actors
    if req.events:
        existing["events"] = req.events
    if req.obligations:
        existing["obligations"] = req.obligations
    if req.missing_details is not None:
        existing["missing_details"] = req.missing_details
    if req.potential_ambiguities is not None:
        existing["potential_ambiguities"] = req.potential_ambiguities

    store.save_artifact(desc_id, "summary.json", existing)
    return {"status": "updated", "summary": existing}


# ── Step 3: Clarification Wizard ────────────────────────────────────

@router.get("/questions/{desc_id}")
def get_questions(desc_id: str):
    """Generate clarification questions based on missing/ambiguous fields."""
    data = store.load_artifact(desc_id, "summary.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Summary not found.")

    summary = ScenarioSummary.from_dict(data)
    questions = generate_questions(summary)

    # Save questions for later answer application
    store.save_artifact(
        desc_id, "questions.json", [q.to_dict() for q in questions]
    )

    return {
        "questions": [q.to_dict() for q in questions],
        "total": len(questions),
    }


@router.post("/answers/{desc_id}")
def submit_answers(desc_id: str, req: AnswersRequest):
    """Submit answers to clarification questions and update obligations."""
    # Load summary, questions, provenance
    summary_data = store.load_artifact(desc_id, "summary.json")
    questions_data = store.load_artifact(desc_id, "questions.json")
    provenance_data = store.load_artifact(desc_id, "provenance.json")

    if summary_data is None:
        raise HTTPException(status_code=404, detail="Summary not found.")

    summary = ScenarioSummary.from_dict(summary_data)
    questions = [ClarificationQuestion.from_dict(q) for q in (questions_data or [])]
    provenance = [ProvenanceRecord.from_dict(p) for p in (provenance_data or [])]

    # Convert request answers to schema objects
    answers = [
        ClarificationAnswer(
            question_id=a.question_id,
            answer_text=a.answer_text,
            selected_options=a.selected_options,
        )
        for a in req.answers
    ]

    # Apply answers to obligations
    updated_obligations = apply_answers(summary.obligations, answers, questions)
    summary.obligations = updated_obligations

    # Update provenance
    provenance = update_provenance_from_answers(
        provenance, summary.obligations, answers, questions
    )

    # Save updated artifacts
    store.save_artifact(desc_id, "summary.json", summary.to_dict())
    store.save_artifact(
        desc_id, "provenance.json", [p.to_dict() for p in provenance]
    )

    return {
        "status": "answers_applied",
        "summary": summary.to_dict(),
        "provenance": [p.to_dict() for p in provenance],
    }


# ── Step 4: Generate Contract ───────────────────────────────────────

@router.post("/generate/{desc_id}")
def generate(desc_id: str):
    """Generate the contract draft (plain-language, IG syntax, JSON)."""
    summary_data = store.load_artifact(desc_id, "summary.json")
    provenance_data = store.load_artifact(desc_id, "provenance.json")

    if summary_data is None:
        raise HTTPException(status_code=404, detail="Summary not found.")

    summary = ScenarioSummary.from_dict(summary_data)
    provenance = [ProvenanceRecord.from_dict(p) for p in (provenance_data or [])]

    try:
        draft = generate_contract(summary, provenance, _get_llm())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contract generation failed: {e}")

    store.save_artifact(desc_id, "draft.json", draft.to_dict())

    return {"draft": draft.to_dict()}


@router.get("/draft/{desc_id}")
def get_draft(desc_id: str):
    """Get the current contract draft."""
    data = store.load_artifact(desc_id, "draft.json")
    if data is None:
        raise HTTPException(status_code=404, detail="Draft not found. Run generate first.")
    return {"draft": data}


# ── Step 5: Validate Contract ───────────────────────────────────────

@router.post("/validate/{desc_id}")
def validate(desc_id: str):
    """Run schema + semantic + repair-site validation on the draft contract."""
    draft_data = store.load_artifact(desc_id, "draft.json")
    if draft_data is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    draft = ContractDraft.from_dict(draft_data)
    result = validate_contract(draft.json_contract)

    store.save_artifact(desc_id, "validation.json", result.to_dict())

    return {"validation": result.to_dict()}


# ── Step 6: Event Vocabulary Mapping ────────────────────────────────

@router.post("/map-events/{desc_id}")
def map_events(desc_id: str, req: MapEventsRequest):
    """Auto-map contract events to trace event names."""
    draft_data = store.load_artifact(desc_id, "draft.json")
    if draft_data is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    draft = ContractDraft.from_dict(draft_data)
    contract_events = get_contract_events_from_json(draft.json_contract)

    mappings = auto_map(contract_events, req.trace_events)

    store.save_artifact(
        desc_id, "event_mappings.json", [m.to_dict() for m in mappings]
    )

    return {
        "mappings": [m.to_dict() for m in mappings],
        "has_unresolved": has_unresolved_mappings(mappings),
    }


@router.post("/confirm-mapping/{desc_id}")
def confirm_event_mapping(desc_id: str, req: ConfirmMappingRequest):
    """Confirm or update a specific event mapping."""
    mappings_data = store.load_artifact(desc_id, "event_mappings.json")
    if mappings_data is None:
        raise HTTPException(status_code=404, detail="No mappings found.")

    mappings = [EventMapping.from_dict(m) for m in mappings_data]
    mappings = confirm_mapping(mappings, req.contract_event, req.trace_events)

    store.save_artifact(
        desc_id, "event_mappings.json", [m.to_dict() for m in mappings]
    )

    return {
        "mappings": [m.to_dict() for m in mappings],
        "has_unresolved": has_unresolved_mappings(mappings),
    }


# ── Step 7: Lock Contract ──────────────────────────────────────────

@router.post("/lock/{desc_id}")
def lock(desc_id: str):
    """Lock the contract for auditing."""
    draft_data = store.load_artifact(desc_id, "draft.json")
    validation_data = store.load_artifact(desc_id, "validation.json")
    provenance_data = store.load_artifact(desc_id, "provenance.json")
    mappings_data = store.load_artifact(desc_id, "event_mappings.json")

    if draft_data is None:
        raise HTTPException(status_code=400, detail="No draft found.")
    if validation_data is None:
        raise HTTPException(status_code=400, detail="No validation result. Validate first.")

    draft = ContractDraft.from_dict(draft_data)
    validation = ValidationResult(**{
        k: v for k, v in validation_data.items() if k != "all_passed"
    })
    provenance = [ProvenanceRecord.from_dict(p) for p in (provenance_data or [])]
    event_mappings = (
        [EventMapping.from_dict(m) for m in mappings_data]
        if mappings_data else None
    )

    try:
        metadata = do_lock(desc_id, draft, validation, provenance, event_mappings)
    except LockError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"metadata": metadata.to_dict(), "status": "locked"}


@router.get("/locked/{desc_id}")
def get_locked(desc_id: str):
    """Get locked contract metadata."""
    meta = get_locked_metadata(desc_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="No locked contract found.")

    contract = get_locked_contract(desc_id)
    ready, reason = can_audit(desc_id)

    return {
        "metadata": meta.to_dict(),
        "contract": contract,
        "can_audit": ready,
        "audit_status": reason,
    }
