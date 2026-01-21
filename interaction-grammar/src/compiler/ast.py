"""
This module defines the Abstract Syntax Tree (AST) nodes for the Interaction Grammar.
It provides a set of dataclasses that represent the various constructs of the language,
allowing for a structured internal representation of interaction contracts.

Classes:
    - ASTNode: The base class for all nodes in the tree.
    - Act: Represents an atomic action with a primitive (σ, ρ, τ, α), an agent, a channel, and an optional object.
    - Seq: Represents a sequential composition of two nodes with an optional latency constraint.
    - Par: Represents a parallel composition of two nodes with optional synchronization constraints.
    - Repair: Represents an error handling strategy with a site identifier, an expression, and an optional retry policy.
    - Neg: Represents the negation or disruption of an interaction expression.
    - Bind: Represents a grouping of multiple interaction nodes sharing a common latency constraint or policy.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from .constraint_parser import LatencyConstraint, SyncConstraint, RetryConstraint

@dataclass
class ASTNode:
    pass

@dataclass
class Act(ASTNode):
    prim: str
    agent: Union[str, List[str]]
    channel: str
    object: Optional[str] = None

@dataclass
class Seq(ASTNode):
    left: ASTNode
    right: ASTNode
    latency: Optional[LatencyConstraint] = None

@dataclass
class Par(ASTNode):
    left: ASTNode
    right: ASTNode
    sync: Optional[Dict[str, SyncConstraint]] = None

@dataclass
class Repair(ASTNode):
    site: str
    expr: ASTNode
    retry: Optional[RetryConstraint] = None

@dataclass
class Neg(ASTNode):
    expr: ASTNode
    disrupt: Optional[str] = None

@dataclass
class Bind(ASTNode):
    items: List[ASTNode]
    latency: Optional[LatencyConstraint] = None
    policy: Optional[Dict[str, Any]] = None
