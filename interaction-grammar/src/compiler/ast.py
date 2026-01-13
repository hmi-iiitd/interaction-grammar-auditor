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
class Bind(ASTNode):
    items: List[ASTNode]
    latency: Optional[LatencyConstraint] = None
    policy: Optional[Dict[str, Any]] = None
