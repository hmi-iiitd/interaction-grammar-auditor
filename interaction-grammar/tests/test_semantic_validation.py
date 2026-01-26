"""
This module contains unit tests for the SemanticValidator, ensuring that interaction contracts
enforce logical constraints such as agent naming conventions and non-negative latencies.

Functions:
    - test_validate_act_valid: Verifies that a correctly formatted action passes semantic validation.
    - test_validate_act_invalid_format: Verifies that an action with an incorrectly formatted agent name (missing underscore) fails.
    - test_validate_act_invalid_type: Verifies that an action with an unknown agent type (not human, robot, system, or env) fails.
    - test_validate_seq_negative_latency: Verifies that a sequence with a negative latency constraint fails.
    - test_validate_act_list_valid: Verifies that an action with a list of valid agents passes semantic validation.
"""

import pytest
from src.compiler.ast import Act, Seq
from src.compiler.constraint_parser import LatencyConstraint
from src.compiler.validator import SemanticValidator, ValidationError

def test_validate_act_valid():
    validator = SemanticValidator()
    act = Act(prim="σ", agent="robot_1", channel="speech")
    validator.validate(act)

def test_validate_act_invalid_format():
    validator = SemanticValidator()
    act = Act(prim="σ", agent="robot1", channel="speech")
    with pytest.raises(ValidationError) as e:
        validator.validate(act)
    assert e.value.code == "E_AGENT_FORMAT"

def test_validate_act_invalid_type():
    validator = SemanticValidator()
    act = Act(prim="σ", agent="alien_1", channel="speech")
    with pytest.raises(ValidationError) as e:
        validator.validate(act)
    assert e.value.code == "E_AGENT_TYPE"

def test_validate_seq_negative_latency():
    validator = SemanticValidator()
    act1 = Act(prim="σ", agent="robot_1", channel="speech")
    act2 = Act(prim="ρ", agent="human_1", channel="speech")
    seq = Seq(left=act1, right=act2, latency=LatencyConstraint(value_ms=-100.0))
    with pytest.raises(ValidationError) as e:
        validator.validate(seq)
    assert e.value.code == "E_LATENCY_NEGATIVE"

def test_validate_act_list_valid():
    validator = SemanticValidator()
    act = Act(prim="σ", agent=["robot_1", "human_1"], channel="speech")
    validator.validate(act)
