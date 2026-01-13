from typing import Dict, Any
from .ast import ASTNode, Act, Seq, Par, Repair, Bind
from .constraint_parser import ConstraintParser

class ContractParser:
    def __init__(self):
        self.constraint_parser = ConstraintParser()

    def parse(self, data: Dict[str, Any]) -> ASTNode:
        node_type = data.get("node")
        
        if node_type == "act":
            return self._parse_act(data)
        elif node_type == "seq":
            return self._parse_seq(data)
        elif node_type == "par":
            return self._parse_par(data)
        elif node_type == "repair":
            return self._parse_repair(data)
        elif node_type == "bind":
            return self._parse_bind(data)
        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def _parse_act(self, data: Dict[str, Any]) -> Act:
        return Act(
            prim=data["prim"],
            agent=data["agent"],
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

    def _parse_bind(self, data: Dict[str, Any]) -> Bind:
        latency = None
        if "latency" in data:
            latency = self.constraint_parser.parse_latency(data["latency"])

        return Bind(
            items=[self.parse(item) for item in data["items"]],
            latency=latency,
            policy=data.get("policy")
        )
