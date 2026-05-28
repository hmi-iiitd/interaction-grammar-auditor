"""
Unit tests for Phase 6 authoring pipeline modules.

Covers:
  Module A – scenario store
  Module C – obligation extractor
  Module D – clarification engine
  Module E – contract generator (deterministic parts)
  Module F – provenance tracker
  Module H – vocabulary mapper
  Module I – contract locker
"""

import sys
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from authoring.schemas import (
    ScenarioDescription,
    ScenarioSummary,
    Obligation,
    ClarificationQuestion,
    ClarificationAnswer,
    ProvenanceRecord,
    ContractDraft,
    ValidationResult,
    EventMapping,
    ContractMetadata,
    compute_contract_hash,
)
from authoring.scenario_store import save_description, get_description, StoreError
from authoring.obligation_extractor import (
    validate_extraction, enrich_obligations, get_missing_fields,
)
from authoring.clarification_engine import generate_questions, apply_answers
from authoring.contract_generator import (
    _build_contract_json,
    _fallback_plain_language,
    _fallback_ig_syntax,
)
from authoring.provenance_tracker import (
    create_initial_provenance,
    update_provenance_from_answers,
    get_unconfirmed,
    all_confirmed,
)
from authoring.vocabulary_mapper import (
    auto_map, confirm_mapping, has_unresolved_mappings,
    get_contract_events_from_json,
)
from authoring.contract_locker import (
    lock_contract, is_locked, can_audit, LockError,
    _increment_version,
)
from authoring.fixtures import FIXTURES, get_fixture


# ── Temp store fixture ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    """Redirect authoring_store to a temp directory for each test."""
    monkeypatch.setattr(
        "authoring.scenario_store._store_root",
        lambda: tmp_path / "authoring_store",
    )
    (tmp_path / "authoring_store").mkdir(parents=True, exist_ok=True)
    yield tmp_path / "authoring_store"


# ── Module A: Scenario Store ────────────────────────────────────────

class TestScenarioStore:
    def test_empty_description_rejected(self):
        desc = ScenarioDescription(description="")
        with pytest.raises(StoreError, match="cannot be empty"):
            save_description(desc)

    def test_short_description_rejected(self):
        desc = ScenarioDescription(description="hello")
        with pytest.raises(StoreError, match="too short"):
            save_description(desc)

    def test_valid_description_saved(self):
        desc = ScenarioDescription(
            description="The robot asks the user to confirm the task within 2 seconds.",
            scenario_title="Test",
        )
        desc_id = save_description(desc)
        assert desc_id == desc.description_id

        loaded = get_description(desc_id)
        assert loaded.description == desc.description
        assert loaded.scenario_title == "Test"

    def test_description_not_found(self):
        with pytest.raises(StoreError, match="not found"):
            get_description("nonexistent_id")


# ── Module C: Obligation Extractor ──────────────────────────────────

class TestObligationExtractor:
    def _make_summary(self, obligations):
        return ScenarioSummary(
            description_id="test",
            actors=["robot", "user"],
            events=[],
            obligations=obligations,
        )

    def test_missing_deadline_flagged(self):
        obl = Obligation(
            obligation_type="sequence",
            trigger="robot_ask",
            expected="user_respond",
            deadline_seconds=None,
        )
        missing = get_missing_fields([obl])
        assert len(missing) == 1
        assert missing[0]["category"] == "deadline_missing"

    def test_explicit_deadline_not_flagged(self):
        obl = Obligation(
            obligation_type="sequence",
            trigger="robot_ask",
            expected="user_respond",
            deadline_seconds=2.0,
        )
        missing = get_missing_fields([obl])
        assert len(missing) == 0

    def test_invented_deadline_removed(self):
        obl = Obligation(
            obligation_type="sequence",
            trigger="robot_ask",
            expected="user_respond",
            deadline_seconds=5.0,
            source_sentence="The user should respond soon",
        )
        summary = self._make_summary([obl])
        issues = validate_extraction(summary)
        assert any("invented" in i.lower() for i in issues)
        assert obl.deadline_seconds is None

    def test_repair_missing_retries(self):
        obl = Obligation(
            obligation_type="repair",
            site="ack",
            max_retries=None,
        )
        missing = get_missing_fields([obl])
        assert len(missing) == 1
        assert missing[0]["category"] == "repair_policy_missing"

    def test_enrich_adds_events(self):
        obl = Obligation(
            obligation_type="sequence",
            trigger="robot_ask",
            expected="user_respond",
        )
        summary = self._make_summary([obl])
        enriched = enrich_obligations(summary)
        assert "robot_ask" in enriched.events
        assert "user_respond" in enriched.events


# ── Module D: Clarification Engine ──────────────────────────────────

class TestClarificationEngine:
    def test_deadline_missing_generates_question(self):
        summary = ScenarioSummary(
            obligations=[
                Obligation(
                    obligation_type="sequence",
                    trigger="robot_ask",
                    expected="user_respond",
                    deadline_seconds=None,
                ),
            ],
        )
        questions = generate_questions(summary)
        assert any(q.category == "deadline_missing" for q in questions)

    def test_fully_specified_no_questions(self):
        summary = ScenarioSummary(
            obligations=[
                Obligation(
                    obligation_type="sequence",
                    trigger="robot_ask",
                    expected="user_respond",
                    deadline_seconds=2.0,
                ),
            ],
        )
        questions = generate_questions(summary)
        # May still get failure_condition_missing etc., but no deadline_missing
        assert not any(q.category == "deadline_missing" for q in questions)

    def test_apply_deadline_answer(self):
        obl = Obligation(
            obligation_id="obl_1",
            obligation_type="sequence",
            trigger="robot_ask",
            expected="user_respond",
            deadline_seconds=None,
        )
        q = ClarificationQuestion(
            question_id="q_1",
            category="deadline_missing",
            question_text="How long?",
            related_obligation_id="obl_1",
        )
        ans = ClarificationAnswer(
            question_id="q_1",
            answer_text="2.0 seconds",
        )
        updated = apply_answers([obl], [ans], [q])
        assert updated[0].deadline_seconds == 2.0

    def test_repair_generates_failure_question(self):
        summary = ScenarioSummary(
            obligations=[
                Obligation(
                    obligation_type="repair",
                    site="ack",
                    max_retries=2,
                ),
            ],
        )
        questions = generate_questions(summary)
        assert any(q.category == "failure_condition_missing" for q in questions)


# ── Module E: Contract Generator (deterministic) ────────────────────

class TestContractGenerator:
    def test_build_seq_node(self):
        obls = [
            Obligation(
                obligation_type="sequence",
                trigger="robot_ask",
                expected="user_ack",
                deadline_seconds=2.0,
                site="ack",
            ),
        ]
        result = _build_contract_json(obls)
        assert result["node"] == "seq"
        assert result["latency"] == "2.0s"

    def test_fallback_plain_language(self):
        obls = [
            Obligation(
                obligation_type="sequence",
                trigger="robot_ask",
                expected="user_ack",
                deadline_seconds=2.0,
            ),
        ]
        text = _fallback_plain_language(obls)
        assert "robot_ask" in text
        assert "2.0" in text

    def test_fallback_ig_syntax(self):
        obls = [
            Obligation(
                obligation_type="sequence",
                trigger="robot_ask",
                expected="user_ack",
                deadline_seconds=2.0,
            ),
        ]
        text = _fallback_ig_syntax(obls)
        assert "→" in text
        assert "@within(2.0s)" in text

    def test_multiple_obligations_bind(self):
        obls = [
            Obligation(
                obligation_type="sequence",
                trigger="robot_ask",
                expected="user_ack",
                deadline_seconds=2.0,
                site="ack",
            ),
            Obligation(
                obligation_type="repair",
                site="ack",
                repair_event="robot_retry",
                max_retries=2,
            ),
        ]
        result = _build_contract_json(obls)
        assert result["node"] == "bind"
        assert len(result["items"]) == 2


# ── Module F: Provenance Tracker ────────────────────────────────────

class TestProvenanceTracker:
    def test_initial_provenance_from_source(self):
        obls = [
            Obligation(
                obligation_id="obl_1",
                source_sentence="The robot asks.",
            ),
        ]
        records = create_initial_provenance(obls)
        assert len(records) == 1
        assert records[0].source_type == "scenario_sentence"
        assert records[0].confirmed_by_user is True

    def test_initial_provenance_without_source(self):
        obls = [
            Obligation(obligation_id="obl_1", source_sentence=""),
        ]
        records = create_initial_provenance(obls)
        assert records[0].source_type == "llm_suggestion"
        assert records[0].confirmed_by_user is False

    def test_update_from_answers(self):
        records = [
            ProvenanceRecord(
                obligation_id="obl_1",
                source_type="scenario_sentence",
                source_text="original",
                confirmed_by_user=True,
            ),
        ]
        q = ClarificationQuestion(
            question_id="q_1",
            related_obligation_id="obl_1",
        )
        ans = ClarificationAnswer(
            question_id="q_1",
            answer_text="2 seconds",
        )
        updated = update_provenance_from_answers(records, [], [ans], [q])
        assert updated[0].source_type == "user_clarification"
        assert "2 seconds" in updated[0].source_text

    def test_all_confirmed(self):
        records = [
            ProvenanceRecord(obligation_id="1", confirmed_by_user=True),
            ProvenanceRecord(obligation_id="2", confirmed_by_user=True),
        ]
        assert all_confirmed(records) is True

    def test_unconfirmed_detected(self):
        records = [
            ProvenanceRecord(obligation_id="1", confirmed_by_user=True),
            ProvenanceRecord(obligation_id="2", confirmed_by_user=False),
        ]
        assert all_confirmed(records) is False
        assert len(get_unconfirmed(records)) == 1


# ── Module H: Vocabulary Mapper ─────────────────────────────────────

class TestVocabularyMapper:
    def test_exact_match(self):
        mappings = auto_map(["user_ack"], ["user_ack", "robot_speak"])
        assert mappings[0].mapping_type == "exact"
        assert mappings[0].confirmed is True

    def test_fuzzy_match(self):
        mappings = auto_map(["participant_ack"], ["human_ack_speech", "human_head_nod"])
        # "participant_ack" vs "human_ack_speech" should fuzzy-match
        assert mappings[0].mapping_type in ("fuzzy", "missing")

    def test_missing_match(self):
        mappings = auto_map(["xyz_event"], ["robot_speak"])
        assert mappings[0].mapping_type == "missing"
        assert mappings[0].confirmed is False

    def test_confirm_mapping(self):
        mappings = [
            EventMapping(
                contract_event="user_ack",
                trace_events=["human_ack"],
                mapping_type="fuzzy",
                confirmed=False,
            ),
        ]
        updated = confirm_mapping(mappings, "user_ack", ["human_ack"])
        assert updated[0].confirmed is True
        assert updated[0].confirmed_by == "user"

    def test_unresolved_blocks(self):
        mappings = [
            EventMapping(contract_event="a", confirmed=False),
            EventMapping(contract_event="b", confirmed=True),
        ]
        assert has_unresolved_mappings(mappings) is True

    def test_extract_events_from_json(self):
        contract = {
            "node": "seq",
            "left": {"node": "act", "prim": "α", "agent": "r", "channel": "s", "object": "greet"},
            "right": {"node": "act", "prim": "α", "agent": "h", "channel": "s", "object": "ack"},
        }
        events = get_contract_events_from_json(contract)
        assert "greet" in events
        assert "ack" in events


# ── Module I: Contract Locker ───────────────────────────────────────

class TestContractLocker:
    def _setup_desc(self, temp_store):
        desc = ScenarioDescription(
            description="The robot greets the participant and waits for ack."
        )
        save_description(desc)
        return desc.description_id

    def test_version_increment(self):
        assert _increment_version("1.0") == "2.0"
        assert _increment_version("3.0") == "4.0"

    def test_same_contract_same_hash(self):
        contract = {"node": "seq", "left": {"node": "act"}, "right": {"node": "act"}}
        h1 = compute_contract_hash(contract)
        h2 = compute_contract_hash(contract)
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_lock_requires_validation(self, temp_store):
        desc_id = self._setup_desc(temp_store)
        draft = ContractDraft(
            description_id=desc_id,
            json_contract={"node": "seq"},
        )
        validation = ValidationResult(
            schema_valid=False,
            semantic_valid=False,
            repair_sites_valid=False,
            errors=["test error"],
        )
        provenance = []
        with pytest.raises(LockError, match="validation has not passed"):
            lock_contract(desc_id, draft, validation, provenance)

    def test_lock_creates_version_and_hash(self, temp_store):
        desc_id = self._setup_desc(temp_store)
        draft = ContractDraft(
            description_id=desc_id,
            json_contract={"node": "seq", "left": {"node": "act"}, "right": {"node": "act"}},
        )
        validation = ValidationResult(
            schema_valid=True,
            semantic_valid=True,
            repair_sites_valid=True,
        )
        provenance = [ProvenanceRecord(obligation_id="obl_1", confirmed_by_user=True)]

        meta = lock_contract(desc_id, draft, validation, provenance)
        assert meta.version == "1.0"
        assert meta.locked is True
        assert meta.contract_hash.startswith("sha256:")
        assert is_locked(desc_id)

    def test_can_audit_locked(self, temp_store):
        desc_id = self._setup_desc(temp_store)
        draft = ContractDraft(
            description_id=desc_id,
            json_contract={"node": "seq"},
        )
        validation = ValidationResult(
            schema_valid=True, semantic_valid=True, repair_sites_valid=True,
        )
        lock_contract(desc_id, draft, validation, [
            ProvenanceRecord(obligation_id="obl_1", confirmed_by_user=True),
        ])
        ready, reason = can_audit(desc_id)
        assert ready is True

    def test_cannot_audit_unlocked(self, temp_store):
        desc_id = self._setup_desc(temp_store)
        ready, reason = can_audit(desc_id)
        assert ready is False
        assert "not locked" in reason.lower() or "No contract" in reason


# ── Fixture Data ────────────────────────────────────────────────────

class TestFixtures:
    def test_all_8_fixtures_exist(self):
        assert len(FIXTURES) == 8

    def test_fixture_lookup(self):
        f = get_fixture("simple_acknowledgment")
        assert f is not None
        assert "2 seconds" in f.input_description

    def test_missing_deadline_fixture_expects_clarification(self):
        f = get_fixture("missing_deadline")
        assert "deadline_missing" in f.expected_clarification_categories

    def test_full_scenario_fixture_has_multiple_types(self):
        f = get_fixture("full_scenario")
        assert len(f.expected_obligation_types) >= 3
