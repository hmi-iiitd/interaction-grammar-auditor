"""
This module implements the core auditing logic for interaction contracts.
It traverses the AST and validates the trace against the contract's structure and constraints.
"""

from typing import Dict, Any, Optional, List, Union, Tuple
from src.compiler.ast import ASTNode, Act, Seq, Par, Repair, Bind, Neg
from src.audit.trace import Trace, Event
from src.audit.matcher import EventMatcher

class AuditVerdict:
    PASS = "PASS"
    FAIL = "FAIL"

class AuditResult:
    def __init__(self, verdict: str, code: Optional[str] = None, 
                 clause_path: str = "$", expected: Optional[Dict] = None, 
                 observed: Optional[Dict] = None, witness: Optional[Dict] = None):
        self.verdict = verdict
        self.code = code
        self.clause_path = clause_path
        self.expected = expected or {}
        self.observed = observed or {}
        self.witness = witness or {}

    def to_dict(self) -> Dict[str, Any]:
        res = {"verdict": self.verdict}
        if self.verdict == AuditVerdict.FAIL:
             res.update({
                 "code": self.code,
                 "clause_path": self.clause_path,
                 "expected": self.expected,
                 "observed": self.observed,
                 "witness": self.witness
             })
        return res

class Auditor:
    def __init__(self, contract: ASTNode):
        self.contract = contract

    def audit(self, trace: Trace) -> AuditResult:
        """Top-level audit function."""
        # For Phase 2, we assume the root is a single interaction.
        # We need to find the *first* occurrence that satisfies the root.
        # This is a simplification; in reality, we might search for all valid interactions.
        return self._check_node(self.contract, trace, start_idx=0, path="$")

    def _check_node(self, node: ASTNode, trace: Trace, start_idx: int, path: str) -> AuditResult:
        if isinstance(node, Act):
            return self._check_act(node, trace, start_idx, path)
        elif isinstance(node, Seq):
            return self._check_seq(node, trace, start_idx, path)
        elif isinstance(node, Par):
            return self._check_par(node, trace, start_idx, path)
        elif isinstance(node, Repair):
             # For Phase 2, we just verify the main expression and ignore repair logic for now (or treat as seq)
             # But the prompt says "don't audit repair yet", so we might just pass through to expr
             return self._check_node(node.expr, trace, start_idx, path + ".expr")
        elif isinstance(node, Neg):
            return self._check_neg(node, trace, start_idx, path)
        elif isinstance(node, Bind):
            return self._check_bind(node, trace, start_idx, path)
        else:
             raise ValueError(f"Unknown AST node type: {type(node)}")

    def _check_act(self, node: Act, trace: Trace, start_idx: int, path: str) -> AuditResult:
        """Find the first matching event in the trace starting from start_idx."""
        for i in range(start_idx, len(trace)):
            event = trace[i]
            if EventMatcher.match_act(node, event):
                return AuditResult(
                    AuditVerdict.PASS,
                    witness={"idx": i, "event": event.to_dict()}
                )
        
        # Not found
        return AuditResult(
            AuditVerdict.FAIL,
            code="V_ACT_MISSING",
            clause_path=path,
            expected={"act": f"{node.prim}({node.agent},{node.channel})"},
            observed={"trace_len": len(trace), "searched_from": start_idx}
        )

    def _check_seq(self, node: Seq, trace: Trace, start_idx: int, path: str) -> AuditResult:
        # 1. Find Left
        res_left = self._check_node(node.left, trace, start_idx, path + ".left")
        if res_left.verdict == AuditVerdict.FAIL:
            return res_left # Propagate failure

        left_idx = res_left.witness["idx"]
        left_event = res_left.witness["event"]
        
        # 2. Find Right (must be strictly after Left)
        # Note: strictly after means index > left_idx.
        # Timestamps might be identical if events are simultaneous, but order in trace matters.
        res_right = self._check_node(node.right, trace, left_idx + 1, path + ".right")
        
        if res_right.verdict == AuditVerdict.FAIL:
             # Transform generic ACT_MISSING to SEQ_MISSING_RIGHT for better clarity
             return AuditResult(
                 AuditVerdict.FAIL,
                 code="V_SEQ_MISSING_RIGHT",
                 clause_path=path,
                 expected={"right": "Present after left"},
                 observed={"after_left_until": trace[-1].t if len(trace) > 0 else 0.0},
                 witness={"left_event": left_event}
             )

        right_idx = res_right.witness["idx"]
        right_event = res_right.witness["event"]

        # 3. Check Latency
        if node.latency:
             dt = right_event["t"] - left_event["t"]
             # We only handle numeric latency in Phase 2 for now, or symbolic if we had values
             # But the AST stores LatencyConstraint object.
             # Assuming value_ms is populated (parsed from string)
             limit_ms = node.latency.value_ms
             
             if limit_ms is not None:
                 limit_sec = limit_ms / 1000.0
                 # Use a small epsilon for float comparison?
                 if dt > limit_sec + 1e-6:
                     return AuditResult(
                         AuditVerdict.FAIL,
                         code="V_SEQ_LATENCY",
                         clause_path=path,
                         expected={"latency_leq": f"{limit_sec}s"},
                         observed={"dt": dt},
                         witness={"left_event": left_event, "right_event": right_event}
                     )

        # PASS
        return AuditResult(
            AuditVerdict.PASS,
            witness={"left": res_left.witness, "right": res_right.witness, "idx": right_idx} 
            # We return the rightmost index as the "end" of this sequence
        )

    def _check_par(self, node: Par, trace: Trace, start_idx: int, path: str) -> AuditResult:
        # For Par, we need to find both Left and Right independently starting from start_idx
        # Then check sync constraints.
        
        res_left = self._check_node(node.left, trace, start_idx, path + ".left")
        if res_left.verdict == AuditVerdict.FAIL:
             return AuditResult(
                 AuditVerdict.FAIL,
                 code="V_PAR_MISSING_LEFT",
                 clause_path=path,
                 expected={"left": "Present"},
                 observed={"searched_from": start_idx}
             )
             
        res_right = self._check_node(node.right, trace, start_idx, path + ".right")
        if res_right.verdict == AuditVerdict.FAIL:
             return AuditResult(
                 AuditVerdict.FAIL,
                 code="V_PAR_MISSING_RIGHT",
                 clause_path=path,
                 expected={"right": "Present"},
                 observed={"searched_from": start_idx}
             )

        left_event = res_left.witness["event"]
        right_event = res_right.witness["event"]

        # Check Sync (Start)
        if node.sync and "start" in node.sync:
            sync_constraint = node.sync["start"]
            limit_ms = sync_constraint.value_ms
            
            if limit_ms is not None:
                limit_sec = limit_ms / 1000.0
                diff = abs(left_event["t"] - right_event["t"])
                
                if diff > limit_sec + 1e-6:
                     return AuditResult(
                         AuditVerdict.FAIL,
                         code="V_PAR_SYNC_START",
                         clause_path=path,
                         expected={"sync_start_leq": f"{limit_sec}s"},
                         observed={"dt": diff},
                         witness={"left_event": left_event, "right_event": right_event}
                     )

        # Sync (End) - Phase 2 simplification: treat events as instantaneous, so end sync is same as start?
        # The prompt says: "treat event as instantaneous, so end sync is same as start OR ignore end"
        # We'll ignore end for now unless explicitly needed.

        # PASS
        # The "end" of a parallel block is the max of the two indices
        max_idx = max(res_left.witness["idx"], res_right.witness["idx"])
        return AuditResult(
            AuditVerdict.PASS,
            witness={"left": res_left.witness, "right": res_right.witness, "idx": max_idx}
        )

    def _check_neg(self, node: Neg, trace: Trace, start_idx: int, path: str) -> AuditResult:
        """
        Negation audit: the inner expression must NOT be satisfiable.
        PASS if inner expr fails to match; FAIL if it matches (with witness).
        """
        inner = self._check_node(node.expr, trace, start_idx, path + ".expr")
        if inner.verdict == AuditVerdict.PASS:
            # Inner matched → negation violated
            return AuditResult(
                AuditVerdict.FAIL,
                code="V_NEG_VIOLATED",
                clause_path=path,
                expected={"negated_expr": "should NOT match"},
                observed={"matched": True},
                witness=inner.witness,
            )
        # Inner failed to match → negation satisfied
        return AuditResult(AuditVerdict.PASS, witness={"neg": True, "idx": start_idx})

    def _check_bind(self, node: Bind, trace: Trace, start_idx: int, path: str) -> AuditResult:
        """
        Bind audit: N-ary parallel — all items must be independently present.
        Then optionally checks:
          - latency: span from earliest to latest event ≤ budget
          - policy (k_sync): all pairwise timestamp diffs ≤ delta
          - policy (leader_skew): all followers within epsilon of leader
        """
        results = []
        for i, item in enumerate(node.items):
            r = self._check_node(item, trace, start_idx, f"{path}.items[{i}]")
            if r.verdict == AuditVerdict.FAIL:
                return AuditResult(
                    AuditVerdict.FAIL,
                    code="V_BIND_ITEM_MISSING",
                    clause_path=path,
                    expected={"item_index": i, "item": "Present"},
                    observed={"searched_from": start_idx},
                )
            results.append(r)

        # Collect event dicts and timestamps from witnesses
        events = [r.witness["event"] for r in results]
        timestamps = [e["t"] for e in events]
        max_idx = max(r.witness["idx"] for r in results)

        # Check latency (span from min to max timestamp)
        if node.latency:
            span = max(timestamps) - min(timestamps)
            limit_ms = node.latency.value_ms
            if limit_ms is not None:
                limit_sec = limit_ms / 1000.0
                if span > limit_sec + 1e-6:
                    return AuditResult(
                        AuditVerdict.FAIL,
                        code="V_BIND_LATENCY",
                        clause_path=path,
                        expected={"latency_leq": f"{limit_sec}s"},
                        observed={"span": span},
                        witness={"events": events},
                    )

        # Check policy constraints
        if node.policy:
            policy_name = node.policy.get("name")

            if policy_name == "k_sync":
                delta_constraint = node.policy.get("delta")
                if (delta_constraint
                        and hasattr(delta_constraint, "value_ms")
                        and delta_constraint.value_ms is not None):
                    delta_sec = delta_constraint.value_ms / 1000.0
                    for a in range(len(timestamps)):
                        for b in range(a + 1, len(timestamps)):
                            diff = abs(timestamps[a] - timestamps[b])
                            if diff > delta_sec + 1e-6:
                                return AuditResult(
                                    AuditVerdict.FAIL,
                                    code="V_BIND_POLICY_K_SYNC",
                                    clause_path=path,
                                    expected={"policy": "k_sync", "delta_leq": f"{delta_sec}s"},
                                    observed={"pair": [a, b], "diff": diff},
                                    witness={"events": events},
                                )

            elif policy_name == "leader_skew":
                leader = node.policy.get("leader")
                epsilon_constraint = node.policy.get("epsilon")
                if (leader and epsilon_constraint
                        and hasattr(epsilon_constraint, "value_ms")
                        and epsilon_constraint.value_ms is not None):
                    eps_sec = epsilon_constraint.value_ms / 1000.0
                    # Find leader timestamp
                    leader_t = None
                    for e in events:
                        if e.get("agent") == leader:
                            leader_t = e["t"]
                            break
                    if leader_t is not None:
                        for i, e in enumerate(events):
                            if e.get("agent") != leader:
                                skew = e["t"] - leader_t
                                if skew < -1e-6 or skew > eps_sec + 1e-6:
                                    return AuditResult(
                                        AuditVerdict.FAIL,
                                        code="V_BIND_POLICY_LEADER_SKEW",
                                        clause_path=path,
                                        expected={"policy": "leader_skew", "epsilon_leq": f"{eps_sec}s"},
                                        observed={"item_index": i, "skew": skew},
                                        witness={"events": events},
                                    )

        return AuditResult(
            AuditVerdict.PASS,
            witness={"items": [r.witness for r in results], "idx": max_idx}
        )
