"""
This module contains the ContractParser class, which is responsible for converting
JSON-based interaction contracts into a typed Abstract Syntax Tree (AST).

Classes:
    - ContractParser: The main parser class that orchestrates the conversion process.

Functions in ContractParser:
    - __init__: Initializes the parser and its dependency, ConstraintParser.
    - parse: The entry point for parsing a JSON dictionary. It uses dynamic dispatch to call specific _parse_* methods based on the "node" type.
    - _parse_act: Parses an 'act' node into an Act AST node, handling agent group parsing.
    - _parse_seq: Parses a 'seq' node into a Seq AST node, including its latency constraint.
    - _parse_par: Parses a 'par' node into a Par AST node, including its synchronization constraints.
    - _parse_repair: Parses a 'repair' node into a Repair AST node, including its retry policy.
    - _parse_neg: Parses a 'neg' node into a Neg AST node.
    - _parse_bind: Parses a 'bind' node into a Bind AST node, handling shared latency and policy parameters.
"""

from typing import Dict, Any
from .ast import ASTNode, Act, Seq, Par, Repair, Bind, Neg
from .constraint_parser import ConstraintParser

class ContractParser:
    def __init__(self):
        self.constraint_parser = ConstraintParser()

    def parse(self, data: Dict[str, Any]) -> ASTNode:
        node_type = data.get("node")
        if not node_type:
            raise ValueError("Node type missing in data")
        
        method_name = f"_parse_{node_type}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(data)
        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def _parse_act(self, data: Dict[str, Any]) -> Act:
        return Act(
            prim=data["prim"],
            agent=self.constraint_parser.parse_agents(data["agent"]),
            channel=data["channel"],
            object=data.get("object")
        )

    def _parse_seq(self, data: Dict[str, Any]) -> Seq:
        latency = None
        if "latency" in data:
            latency = self.constraint_parser.parse_latency(data["latency"])
            
        return Seq(
            left=self.parse(data["left"]),
            right=self.parse(data["right"]),
            latency=latency
        )

    def _parse_par(self, data: Dict[str, Any]) -> Par:
        sync = None
        if "sync" in data:
            sync = {}
            for k, v in data["sync"].items():
                constraint = self.constraint_parser.parse_sync(v)
                constraint.type = k # Set the type based on the key
                sync[k] = constraint

        return Par(
            left=self.parse(data["left"]),
            right=self.parse(data["right"]),
            sync=sync
        )

    def _parse_repair(self, data: Dict[str, Any]) -> Repair:
        # Retry is a dict in JSON, but we might want to parse its values if they were strings
        # Currently in JSON it's {"N_leq": 2, "mu_leq": 0.2} (numbers)
        # So we can just map it to RetryConstraint
        retry = None
        if "retry" in data:
            retry_data = data["retry"]
            # Pass the dict directly to constraint parser, which will convert to string and parse with grammar
            retry = self.constraint_parser.parse_retry(retry_data)

        return Repair(
            site=data["site"],
            expr=self.parse(data["expr"]),
            retry=retry
        )

    def _parse_neg(self, data: Dict[str, Any]) -> Neg:
        return Neg(
            expr=self.parse(data["expr"]),
            disrupt=data.get("disrupt")
        )

    def _parse_bind(self, data: Dict[str, Any]) -> Bind:
        latency = None
        if "latency" in data:
            latency = self.constraint_parser.parse_latency(data["latency"])

        policy = data.get("policy")
        if policy:
            # Parse delta and epsilon in policy if they are strings
            if "delta" in policy and isinstance(policy["delta"], str):
                policy["delta"] = self.constraint_parser.parse_latency(policy["delta"])
            if "epsilon" in policy and isinstance(policy["epsilon"], str):
                policy["epsilon"] = self.constraint_parser.parse_latency(policy["epsilon"])

        return Bind(
            items=[self.parse(item) for item in data["items"]],
            latency=latency,
            policy=policy
        )
