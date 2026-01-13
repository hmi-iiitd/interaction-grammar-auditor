from lark import Lark, Transformer, v_args
from dataclasses import dataclass
from typing import Optional, Union, Dict
from pathlib import Path

# Load authoritative grammar
GRAMMAR_PATH = Path(__file__).parent.parent.parent / "grammar" / "grammar.lark"

@dataclass
class LatencyConstraint:
    value_ms: float

@dataclass
class SyncConstraint:
    type: str  # 'start' or 'end'
    value_ms: float

@dataclass
class RetryConstraint:
    n_max: Optional[int] = None
    mu_max: Optional[float] = None

class ConstraintTransformer(Transformer):
    def delta(self, args):
        # args[0] is NUMBER, args[1] is UNIT (optional)
        val = float(args[0])
        unit = args[1] if len(args) > 1 else "ms"
        return self._to_ms(val, unit)

    def delta_like(self, args):
        # Similar to delta for now
        val = float(args[0])
        unit = args[1] if len(args) > 1 else "ms"
        return self._to_ms(val, unit)

    def sync_start(self, args):
        return SyncConstraint(type='start', value_ms=args[0])

    def sync_end(self, args):
        return SyncConstraint(type='end', value_ms=args[0])

    def retry_args(self, args):
        # args will be a list of results from children
        # grammar: "N≤" INT ["," "μ≤" NUMBER]
        n_max = None
        mu_max = None
        for arg in args:
            if isinstance(arg, int):
                n_max = arg
            elif isinstance(arg, float):
                mu_max = arg
        return RetryConstraint(n_max=n_max, mu_max=mu_max)

    def latency_val(self, args):
        return args[0]

    def sync_val(self, args):
        return args[0]

    def INT(self, token):
        return int(token)

    def NUMBER(self, token):
        return float(token)

    def UNIT(self, token):
        return str(token)

    def _to_ms(self, val: float, unit: str) -> float:
        if unit == "ms": return val
        if unit == "s": return val * 1000
        if unit == "m": return val * 60000
        return val

class ConstraintParser:
    def __init__(self):
        with open(GRAMMAR_PATH, 'r') as f:
            self.grammar = f.read()
        
        # Extend grammar to handle JSON fragments directly
        # This avoids manual string manipulation (like stripping "≤")
        self.grammar += """
        latency_val: "≤" delta
        sync_val: "≤" delta_like
        """
        
        self.parser = Lark(self.grammar, start=['latency_val', 'sync_val', 'retry_args'], parser='lalr')
        self.transformer = ConstraintTransformer()

    def parse_latency(self, text: str) -> LatencyConstraint:
        # Parse "≤2s" directly using the extended grammar rule
        tree = self.parser.parse(text, start='latency_val')
        val_ms = self.transformer.transform(tree)
        return LatencyConstraint(value_ms=val_ms)

    def parse_sync(self, text: str) -> SyncConstraint:
        # Parse "≤300ms" directly using the extended grammar rule
        tree = self.parser.parse(text, start='sync_val')
        val_ms = self.transformer.transform(tree)
        return SyncConstraint(type='unknown', value_ms=val_ms)

    def parse_retry(self, text: str) -> RetryConstraint:
        # JSON: "retry": { "N_leq": 2, "mu_leq": 0.2 }
        # Convert dict to string format matching grammar: "N≤2, μ≤0.2"
        if isinstance(text, dict):
            parts = []
            if "N_leq" in text:
                parts.append(f"N≤{text['N_leq']}")
            if "mu_leq" in text:
                parts.append(f"μ≤{text['mu_leq']}")
            text = ", ".join(parts)
            
        tree = self.parser.parse(text, start='retry_args')
        return self.transformer.transform(tree)
