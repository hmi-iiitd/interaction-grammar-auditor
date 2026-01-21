"""
This module provides validation logic for interaction contracts, including schema-based
validation and deep semantic checks.

Classes:
    - SchemaValidator: Validates JSON contract data against a predefined JSON schema.
    - SemanticValidator: Performs deep semantic checks on the Abstract Syntax Tree (AST) to ensure logical correctness.

Functions in SchemaValidator:
    - __init__: Initializes the validator with the path to the JSON schema file.
    - validate: Validates a JSON dictionary against the schema, with specific error handling for node-specific requirements.

Functions in SemanticValidator:
    - validate: The entry point for semantic validation. It uses dynamic dispatch to call specific _validate_* methods based on the AST node type.
    - _validate_act: Checks agent naming formats and types (human, robot, system, env).
    - _validate_seq: Ensures non-negative latency and recursively validates child nodes.
    - _validate_par: Ensures non-negative synchronization tolerances and recursively validates child nodes.
    - _validate_neg: Recursively validates the negated expression.
    - _validate_repair: Checks retry parameters (n_max, mu_max) and recursively validates the expression.
    - _validate_bind: Ensures non-negative latency and recursively validates all bound items.
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, Any, List, Union
from .ast import ASTNode, Act, Seq, Par, Repair, Bind, Neg

class SchemaValidator:
    def __init__(self, schema_path: str):
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)

    def validate(self, instance: Dict[str, Any]) -> None:
        node_type = instance.get("node")
        if node_type:
            # Dynamically discover mapping from $defs by looking for 'const' in 'node' property
            type_map = {}
            for def_name, def_val in self.schema.get("$defs", {}).items():
                properties = def_val.get("properties", {})
                node_const = properties.get("node", {}).get("const")
                if node_const:
                    type_map[node_const] = def_name
            
            if node_type in type_map:
                def_name = type_map[node_type]
                sub_schema = self.schema["$defs"][def_name]
                resolver = jsonschema.validators.RefResolver.from_schema(self.schema)
                try:
                    jsonschema.validate(instance=instance, schema=sub_schema, resolver=resolver)
                except jsonschema.ValidationError as e:
                    if e.validator == "required":
                        required_fields = sub_schema.get("required", [])
                        raise jsonschema.ValidationError(
                            f"Schema requires {required_fields} for '{node_type}' node."
                        )
                    raise e
                return

        jsonschema.validate(instance=instance, schema=self.schema)

class SemanticValidator:
    def validate(self, node: ASTNode) -> None:
        method_name = f"_validate_{node.__class__.__name__.lower()}"
        if hasattr(self, method_name):
            getattr(self, method_name)(node)

    def _validate_act(self, node: Act) -> None:
        # Check agent format: type_index
        agents = node.agent if isinstance(node.agent, list) else [node.agent]
        for agent in agents:
            if "_" not in agent:
                raise ValueError(f"Invalid agent format: {agent}. Expected 'type_index' (e.g., robot_1)")
            parts = agent.split("_")
            if parts[0] not in ["human", "robot", "system", "env"]:
                raise ValueError(f"Invalid agent type: {parts[0]}. Must be human, robot, system, or env")
            if not parts[1].isdigit():
                raise ValueError(f"Invalid agent index: {parts[1]}. Must be an integer")

    def _validate_seq(self, node: Seq) -> None:
        if node.latency and node.latency.value_ms < 0:
            raise ValueError(f"Latency cannot be negative: {node.latency.value_ms}")
        self.validate(node.left)
        self.validate(node.right)

    def _validate_par(self, node: Par) -> None:
        if node.sync:
            for k, v in node.sync.items():
                if v.value_ms < 0:
                    raise ValueError(f"Sync tolerance cannot be negative: {v.value_ms}")
        self.validate(node.left)
        self.validate(node.right)

    def _validate_neg(self, node: Neg) -> None:
        self.validate(node.expr)

    def _validate_repair(self, node: Repair) -> None:
        if node.retry:
            if node.retry.n_max < 0:
                raise ValueError(f"Retry n_max cannot be negative: {node.retry.n_max}")
            if node.retry.mu_max is not None and node.retry.mu_max < 0:
                raise ValueError(f"Retry mu_max cannot be negative: {node.retry.mu_max}")
        self.validate(node.expr)

    def _validate_bind(self, node: Bind) -> None:
        if node.latency and node.latency.value_ms < 0:
            raise ValueError(f"Latency cannot be negative: {node.latency.value_ms}")
        for item in node.items:
            self.validate(item)
