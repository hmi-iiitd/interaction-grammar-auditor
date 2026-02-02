"""
This module provides validation logic for interaction contracts, including schema-based
validation and deep semantic checks.

Classes:
    - ValidationError: Custom exception for semantic validation errors with error codes.
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
import re
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from .ast import ASTNode, Act, Seq, Par, Repair, Bind, Neg

class ValidationError(Exception):
    """Custom exception for semantic validation errors with error codes."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

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
    def __init__(self):
        self.repair_sites = set()
    
    def validate(self, node: ASTNode) -> None:
        method_name = f"_validate_{node.__class__.__name__.lower()}"
        if hasattr(self, method_name):
            getattr(self, method_name)(node)
    
    
    def _validate_latency_strings(self, instance: Dict[str, Any]) -> None:
        """Validate latency strings are parseable."""
        node_type = instance.get("node")
        
        # Check latency in seq and bind nodes
        if node_type in ["seq", "bind"] and "latency" in instance:
            lat_str = instance["latency"]
            if isinstance(lat_str, str):
                if not self._is_valid_latency(lat_str):
                    raise ValidationError("E_LATENCY_PARSE", 
                        f"Latency string '{lat_str}' cannot be parsed. Expected format: '≤2s', '≤300ms', or 'Δ(id1,id2)'")
        
        # Check sync in par nodes
        if node_type == "par" and "sync" in instance:
            sync_obj = instance["sync"]
            if isinstance(sync_obj, dict):
                for key, val in sync_obj.items():
                    if isinstance(val, str) and not self._is_valid_latency(val):
                        raise ValidationError("E_LATENCY_PARSE", 
                            f"Sync {key} string '{val}' cannot be parsed. Expected format: '≤2s', '≤300ms', or 'δ(id1,id2)'")
        
        # Recursively check child nodes
        if "left" in instance:
            self._validate_latency_strings(instance["left"])
        if "right" in instance:
            self._validate_latency_strings(instance["right"])
        if "expr" in instance:
            self._validate_latency_strings(instance["expr"])
        if "items" in instance and isinstance(instance["items"], list):
            for item in instance["items"]:
                if isinstance(item, dict):
                    self._validate_latency_strings(item)
    
    def _is_valid_latency(self, lat_str: str) -> bool:
        """Check if a latency string is in a valid format."""
        clean = lat_str.replace("≤", "").strip()
        
        # Allow symbolic forms
        if re.match(r'^[Δδ]\([A-Za-z_][A-Za-z0-9_]*\s*,\s*[A-Za-z_][A-Za-z0-9_]*\)$', clean):
            return True
        
        # Allow numeric with optional unit
        if re.match(r'^\d+(?:\.\d+)?\s*(ms|s|m)?$', clean):
            return True
        
        return False

    def _collect_sites(self, node: ASTNode, site_name: Optional[str] = None) -> None:
        """Collect all site names from object fields in Act nodes."""
        if isinstance(node, Act):
            if node.object:
                self.repair_sites.add(node.object)
        elif isinstance(node, Seq):
            self._collect_sites(node.left, site_name)
            self._collect_sites(node.right, site_name)
        elif isinstance(node, Par):
            self._collect_sites(node.left, site_name)
            self._collect_sites(node.right, site_name)
        elif isinstance(node, Neg):
            self._collect_sites(node.expr, site_name)
        elif isinstance(node, Repair):
            self._collect_sites(node.expr, node.site)
        elif isinstance(node, Bind):
            for item in node.items:
                self._collect_sites(item, site_name)

    def _parse_latency_string(self, lat_str: str) -> Optional[float]:
        """Parse latency string to milliseconds. Returns None if unparseable."""
        clean = lat_str.replace("≤", "").strip()
        
        # Check for symbolic forms
        if "Δ" in clean or "δ" in clean:
            return None
        
        # Try to parse numeric with unit
        match = re.match(r'^(\d+(?:\.\d+)?)\s*(ms|s|m)?$', clean)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            if unit == "s":
                return value * 1000
            elif unit == "m":
                return value * 60000
            else:
                return value
        
        return None

    def _validate_act(self, node: Act) -> None:
        # Check if agent is empty list
        if isinstance(node.agent, list):
            if len(node.agent) == 0:
                raise ValidationError("E_AGENT_EMPTY", "Agent list cannot be empty")
            agents = node.agent
        else:
            agents = [node.agent]
        
        # Check agent format: type_index
        for agent in agents:
            if "_" not in agent:
                raise ValidationError("E_AGENT_FORMAT", f"Invalid agent format: {agent}. Expected 'type_index' (e.g., robot_1)")
            parts = agent.split("_")
            if parts[0] not in ["human", "robot", "system", "env"]:
                raise ValidationError("E_AGENT_TYPE", f"Invalid agent type: {parts[0]}. Must be human, robot, system, or env")
            if not parts[1].isdigit():
                raise ValidationError("E_AGENT_INDEX", f"Invalid agent index: {parts[1]}. Must be an integer")

    def _validate_seq(self, node: Seq) -> None:
        if node.latency:
            # Check if latency is parseable
            if node.latency.symbolic:
                # Symbolic latency is allowed
                pass
            elif node.latency.value_ms is not None:
                if node.latency.value_ms < 0:
                    raise ValidationError("E_LATENCY_NEGATIVE", f"Latency cannot be negative: {node.latency.value_ms}")
        
        self.validate(node.left)
        self.validate(node.right)

    def _validate_par(self, node: Par) -> None:
        if node.sync:
            start_ms = None
            end_ms = None
            
            for k, v in node.sync.items():
                if v.value_ms is not None and v.value_ms < 0:
                    raise ValidationError("E_SYNC_NEGATIVE", f"Sync tolerance cannot be negative: {v.value_ms}")
                
                if k == "start" and v.value_ms is not None:
                    start_ms = v.value_ms
                elif k == "end" and v.value_ms is not None:
                    end_ms = v.value_ms
            
            # Check if start tolerance exceeds end tolerance
            if start_ms is not None and end_ms is not None:
                if start_ms > end_ms:
                    raise ValidationError("E_SYNC_INCONSISTENT", 
                        f"Sync start tolerance ({start_ms}ms) cannot exceed end tolerance ({end_ms}ms)")
        
        self.validate(node.left)
        self.validate(node.right)

    def _validate_neg(self, node: Neg) -> None:
        self.validate(node.expr)

    def _validate_repair(self, node: Repair) -> None:
        # Collect all sites first
        self._collect_sites(node.expr)
        
        # Check if repair site exists in the expression
        if node.site not in self.repair_sites:
            raise ValidationError("E_REPAIR_SITE_NOT_FOUND", 
                f"Repair site '{node.site}' not found in expression. Available sites: {sorted(self.repair_sites)}")
        
        if node.retry:
            if node.retry.n_max < 0:
                raise ValidationError("E_RETRY_INVALID", 
                    f"Retry N_leq must be non-negative, got: {node.retry.n_max}")
            if node.retry.mu_max is not None and node.retry.mu_max < 0:
                raise ValidationError("E_RETRY_INVALID", 
                    f"Retry mu_leq must be non-negative, got: {node.retry.mu_max}")
        
        self.validate(node.expr)

    def _validate_bind(self, node: Bind) -> None:
        # Check if bind has at least one constraint
        if not node.latency and not node.policy:
            raise ValidationError("E_BIND_NO_CONSTRAINT", 
                "Bind must have either latency or policy constraint")
        
        if node.latency:
            if node.latency.symbolic:
                pass
            elif node.latency.value_ms is not None and node.latency.value_ms < 0:
                raise ValidationError("E_LATENCY_NEGATIVE", f"Latency cannot be negative: {node.latency.value_ms}")
        
        # Validate policy parameters if present
        if node.policy:
            policy_name = node.policy.get("name")
            if policy_name == "k_sync":
                if "k" not in node.policy or "delta" not in node.policy:
                    raise ValidationError("E_POLICY_PARAMS_MISSING", 
                        "Policy k_sync requires parameters: k and delta")
            elif policy_name == "leader_skew":
                if "leader" not in node.policy or "epsilon" not in node.policy:
                    raise ValidationError("E_POLICY_PARAMS_MISSING", 
                        "Policy leader_skew requires parameters: leader and epsilon")
        
        for item in node.items:
            self.validate(item)
