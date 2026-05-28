"""
Phase 6 Test Fixtures — 8 scenarios from the spec.

Each fixture provides:
  - input_description: raw natural-language scenario
  - expected_actors: actors that should be detected
  - expected_events: key events that should appear
  - expected_obligation_types: obligation types that should be extracted
  - expected_clarification_categories: clarification categories that should fire
  - notes: what the fixture tests
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Fixture:
    name: str
    input_description: str
    scenario_title: str = ""
    robot_platform: str = "NAO"
    interaction_family: str = "turn-taking"
    expected_actors: List[str] = field(default_factory=list)
    expected_events: List[str] = field(default_factory=list)
    expected_obligation_types: List[str] = field(default_factory=list)
    expected_clarification_categories: List[str] = field(default_factory=list)
    notes: str = ""


FIXTURES = [
    # Fixture 1: Simple Acknowledgment
    Fixture(
        name="simple_acknowledgment",
        input_description=(
            "The robot asks the user to confirm the task. "
            "The user should acknowledge within 2 seconds."
        ),
        scenario_title="Simple Acknowledgment",
        expected_actors=["robot", "user"],
        expected_events=[
            "robot_confirmation_request", "user_ack",
        ],
        expected_obligation_types=["sequence"],
        expected_clarification_categories=[],
        notes="Deadline is explicit (2 seconds). No clarification needed.",
    ),

    # Fixture 2: Missing Deadline
    Fixture(
        name="missing_deadline",
        input_description=(
            "The user should respond after the robot asks a question."
        ),
        scenario_title="Missing Deadline",
        expected_actors=["robot", "user"],
        expected_events=[
            "robot_question", "user_response",
        ],
        expected_obligation_types=["sequence"],
        expected_clarification_categories=["deadline_missing"],
        notes="No deadline specified → clarification required.",
    ),

    # Fixture 3: Multimodal Acknowledgment
    Fixture(
        name="multimodal_acknowledgment",
        input_description=(
            "The participant can confirm by saying yes or nodding."
        ),
        scenario_title="Multimodal Acknowledgment",
        expected_actors=["participant"],
        expected_events=[
            "participant_ack", "speech_yes", "head_nod",
        ],
        expected_obligation_types=["alias"],
        expected_clarification_categories=[],
        notes="Modalities are explicit. Alias obligation expected.",
    ),

    # Fixture 4: Repair
    Fixture(
        name="repair",
        input_description=(
            "If the participant does not respond, the robot may retry twice."
        ),
        scenario_title="Repair Scenario",
        expected_actors=["robot", "participant"],
        expected_events=[
            "participant_response", "robot_retry_prompt",
        ],
        expected_obligation_types=["repair"],
        expected_clarification_categories=[],
        notes="Retry count is explicit (2). Repair obligation expected.",
    ),

    # Fixture 5: Interruption
    Fixture(
        name="interruption",
        input_description=(
            "If the participant interrupts while the robot is speaking, "
            "the robot should stop within 0.5 seconds."
        ),
        scenario_title="Interruption Handling",
        expected_actors=["robot", "participant"],
        expected_events=[
            "participant_interrupt", "robot_stop_speaking",
        ],
        expected_obligation_types=["conditional_sequence"],
        expected_clarification_categories=[],
        notes="Deadline and condition are explicit.",
    ),

    # Fixture 6: Ambiguous 'Soon'
    Fixture(
        name="ambiguous_soon",
        input_description=(
            "The robot should respond soon after the participant speaks."
        ),
        scenario_title="Ambiguous Soon",
        expected_actors=["robot", "participant"],
        expected_events=[
            "participant_speech", "robot_response",
        ],
        expected_obligation_types=["sequence"],
        expected_clarification_categories=["deadline_missing"],
        notes="'Soon' is ambiguous → deadline clarification required.",
    ),

    # Fixture 7: Failure After Repair
    Fixture(
        name="failure_after_repair",
        input_description=(
            "If the user still does not acknowledge after two retries, "
            "the interaction should fail."
        ),
        scenario_title="Failure After Repair",
        expected_actors=["user"],
        expected_events=[
            "user_ack",
        ],
        expected_obligation_types=["failure"],
        expected_clarification_categories=[],
        notes="Failure condition with repair exhaustion.",
    ),

    # Fixture 8: Full Scenario
    Fixture(
        name="full_scenario",
        input_description=(
            "The robot greets the participant, asks for task confirmation, "
            "waits for acknowledgment within 2 seconds, retries twice if "
            "missing, and stops if interrupted."
        ),
        scenario_title="Full Scenario",
        robot_platform="NAO",
        interaction_family="turn-taking",
        expected_actors=["robot", "participant"],
        expected_events=[
            "robot_greeting", "robot_confirmation_request",
            "participant_ack", "robot_retry_prompt",
            "participant_interrupt", "robot_stop_speaking",
        ],
        expected_obligation_types=[
            "sequence", "repair", "conditional_sequence",
        ],
        expected_clarification_categories=["deadline_missing"],
        notes=(
            "Multiple obligations. Acknowledgment deadline is explicit (2s) "
            "but interruption stop deadline is missing → clarification."
        ),
    ),
]


def get_fixture(name: str) -> Optional[Fixture]:
    """Get a fixture by name."""
    for f in FIXTURES:
        if f.name == name:
            return f
    return None


def get_all_fixtures() -> List[Fixture]:
    """Get all fixtures."""
    return list(FIXTURES)
