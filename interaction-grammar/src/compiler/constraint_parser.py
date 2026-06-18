"""
This module provides parsing capabilities for string-based constraints in the Interaction Grammar,
leveraging the Lark parsing library and the authoritative grammar definition.

Classes:
    - ConstraintError: Custom exception for constraint parsing errors with error codes.
    - LatencyConstraint: A dataclass representing numeric or symbolic latency.
    - SyncConstraint: A dataclass representing numeric or symbolic synchronization tolerances.
    - RetryConstraint: A dataclass representing retry policies (n_max, mu_max).
    - ConstraintTransformer: A Lark Transformer that converts parse trees into constraint objects.
    - ConstraintParser: The main parser class for various constraint types.

Functions in ConstraintTransformer:
    - delta: Transforms a 'delta' parse tree into a LatencyConstraint.
    - delta_like: Transforms a 'delta_like' parse tree into a SyncConstraint.
    - sync_start/sync_end: Sets the type of a SyncConstraint.
    - retry_args: Transforms retry arguments into a RetryConstraint.
    - agent: Formats agent strings (e.g., robot_1).
    - agent_group: Handles single agents or lists of agents.

Functions in ConstraintParser:
    - __init__: Initializes Lark parsers for latency, sync, retry, and agents using the grammar.
    - parse_latency: Parses a latency string, handling numeric values, symbolic deltas, and malformed inputs.
    - parse_sync: Parses a synchronization constraint string.
    - parse_retry: Parses retry specifications from strings or dictionaries.
    - parse_agents: Parses agent groups from strings or lists.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Union, List
from pathlib import Path
from lark import Lark, Transformer, v_args

class ConstraintError(Exception):
    """Custom exception for constraint parsing errors with error codes."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

@dataclass
class LatencyConstraint:
    value_ms: Optional[float] = None
    symbolic: Optional[str] = None

@dataclass
class SyncConstraint:
    value_ms: Optional[float] = None
    symbolic: Optional[str] = None
    type: str = "start"

@dataclass
class RetryConstraint:
    n_max: int
    mu_max: Optional[float] = None

class ConstraintTransformer(Transformer):
    def delta(self, items):
        # delta: NUMBER [UNIT] | "Δ" "(" IDENT "," IDENT ")"
        if len(items) >= 1 and hasattr(items[0], 'type') and items[0].type == 'NUMBER':
            val = float(items[0])
            if len(items) > 1 and items[1] is not None:
                unit = str(items[1])
                if unit == "s": val *= 1000
                elif unit == "m": val *= 60000
            return LatencyConstraint(value_ms=val)
        elif len(items) == 2: # Δ(id, id)
            return LatencyConstraint(symbolic=f"Δ({items[0]},{items[1]})")
        return LatencyConstraint(value_ms=0.0)

    def delta_like(self, items):
        # delta_like: (NUMBER [UNIT]) | "δ" "(" IDENT "," IDENT ")"
        if isinstance(items[0], LatencyConstraint):
            return SyncConstraint(value_ms=items[0].value_ms, symbolic=items[0].symbolic)
        elif len(items) == 2: # δ(id, id)
            return SyncConstraint(symbolic=f"δ({items[0]},{items[1]})")
        return SyncConstraint(value_ms=0.0)

    def sync_start(self, items):
        res = items[0]
        res.type = "start"
        return res

    def sync_end(self, items):
        res = items[0]
        res.type = "end"
        return res

    def retry_args(self, items):
        n_max = int(items[0])
        mu_max = float(items[1]) if len(items) > 1 and items[1] is not None else None
        return RetryConstraint(n_max=n_max, mu_max=mu_max)

    def agent(self, items):
        return f"{items[0]}_{items[1]}"

    def agent_group(self, items):
        if len(items) == 1:
            return items[0]
        return list(items)

class ConstraintParser:
    def __init__(self):
        grammar_path = Path(__file__).parent.parent.parent / "grammar" / "grammar.lark"
        with open(grammar_path, 'r', encoding='utf-8') as f:
            self.grammar = f.read()
        
        self.latency_lark = Lark(self.grammar, start='delta', parser='lalr', transformer=ConstraintTransformer())
        self.sync_lark = Lark(self.grammar, start='sync_arg', parser='lalr', transformer=ConstraintTransformer())
        self.retry_lark = Lark(self.grammar, start='retry_args', parser='lalr', transformer=ConstraintTransformer())
        self.agent_lark = Lark(self.grammar, start='agent_group', parser='lalr', transformer=ConstraintTransformer())

    def parse_latency(self, lat_str: str) -> LatencyConstraint:
        clean_str = lat_str.replace("≤", "").strip()
        try:
            return self.latency_lark.parse(clean_str)
        except Exception as e:
            try:
                return LatencyConstraint(value_ms=float(clean_str))
            except ValueError:
                if "(" in clean_str or "Δ" in clean_str:
                    raise ConstraintError("E_LATENCY_MALFORMED", 
                        f"Malformed symbolic latency: {lat_str}") from e
                raise ConstraintError("E_LATENCY_PARSE", 
                    f"Cannot parse latency string: {lat_str}") from e

    def parse_sync(self, sync_str: str) -> SyncConstraint:
        clean_str = sync_str.replace("≤", "").strip()
        if "=" not in clean_str:
            try:
                res = self.latency_lark.parse(clean_str)
                return SyncConstraint(value_ms=res.value_ms, symbolic=res.symbolic)
            except Exception:
                try:
                    return SyncConstraint(value_ms=float(clean_str))
                except ValueError:
                    raise ConstraintError("E_SYNC_PARSE", 
                        f"Cannot parse sync constraint: {sync_str}")
        
        try:
            return self.sync_lark.parse(clean_str)
        except Exception as e:
            if "=" in clean_str or "δ" in clean_str:
                raise ConstraintError("E_SYNC_MALFORMED", 
                    f"Malformed sync constraint: {sync_str}") from e
            return SyncConstraint(value_ms=0.0)

    def parse_retry(self, retry_data: Union[str, Dict[str, Any]]) -> RetryConstraint:
        if isinstance(retry_data, dict):
            return RetryConstraint(
                n_max=retry_data.get("N_leq", 0),
                mu_max=retry_data.get("mu_leq")
            )
        try:
            return self.retry_lark.parse(retry_data)
        except Exception as e:
            if "≤" in retry_data or "," in retry_data:
                raise ConstraintError("E_RETRY_MALFORMED", 
                    f"Malformed retry specification: {retry_data}") from e
            raise ConstraintError("E_RETRY_PARSE", 
                f"Cannot parse retry specification: {retry_data}") from e

    def parse_agents(self, agent_data: Union[str, List[str]]) -> Union[str, List[str]]:
        if isinstance(agent_data, list):
            return agent_data
        try:
            return self.agent_lark.parse(agent_data)
        except Exception as e:
            raise ConstraintError("E_AGENT_PARSE", 
                f"Cannot parse agent specification: {agent_data}") from e
