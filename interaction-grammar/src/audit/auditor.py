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
    def __init__(self, verdict: str, 
                 operator: Optional[str] = None,
                 error_code: Optional[str] = None, 
                 clause_path: str = "$", 
                 budget: Optional[str] = None,
                 responsible_agent: Optional[str] = None,
                 expected: Optional[Dict] = None, 
                 observed: Optional[Dict] = None, 
                 witness: Optional[Dict] = None):
        self.verdict = verdict
        self.operator = operator
        self.error_code = error_code
        self.clause_path = clause_path
        self.budget = budget
        self.responsible_agent = responsible_agent
        self.expected = expected or {}
        self.observed = observed or {}
        self.witness = witness or {}

    def to_dict(self) -> Dict[str, Any]:
        res = {"verdict": self.verdict}
        if self.verdict == AuditVerdict.FAIL:
             res.update({
                 "operator": self.operator,
                 "clause_path": self.clause_path,
                 "error_code": self.error_code,
                 "budget": self.budget,
                 "observed": self.observed,
                 "responsible_agent": self.responsible_agent,
                 "expected": self.expected,
                 "witness": self.witness
             })
        return res

class Auditor:
    def __init__(self, contract: ASTNode):
        self.contract = contract

    def audit(self, trace: Trace) -> AuditResult:
        """Top-level audit function."""
        return self._check_node(self.contract, trace, start_idx=0, path="$")

    def _check_node(self, node: ASTNode, trace: Trace, start_idx: int, path: str) -> AuditResult:
        if isinstance(node, Act):
            return self._check_act(node, trace, start_idx, path)
        elif isinstance(node, Seq):
            return self._check_seq(node, trace, start_idx, path)
        elif isinstance(node, Par):
            return self._check_par(node, trace, start_idx, path)
        elif isinstance(node, Repair):
             return self._check_repair(node, trace, start_idx, path)
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
        prim_str = f"{node.prim}({node.agent},{node.channel})"
        resp_agent = node.agent[0] if isinstance(node.agent, list) else str(node.agent)

        return AuditResult(
            AuditVerdict.FAIL,
            operator="act",
            error_code="V_ACT_MISSING",
            clause_path=path,
            responsible_agent=resp_agent,
            expected={"act": prim_str},
            observed={"trace_len": len(trace), "searched_from": start_idx}
        )

    def _check_seq(self, node: Seq, trace: Trace, start_idx: int, path: str) -> AuditResult:
        # 1. Find Left
        res_left = self._check_node(node.left, trace, start_idx, path + ".left")
        if res_left.verdict == AuditVerdict.FAIL:
            return res_left # Propagate failure

        left_idx = res_left.witness["idx"]
        left_t = self._get_start_time(res_left.witness)

        # 2. Find Right (must be strictly after Left)
        res_right = self._check_node(node.right, trace, left_idx + 1, path + ".right")

        if res_right.verdict == AuditVerdict.FAIL:
             if "MISSING" in (res_right.error_code or ""):
                 # CRITICAL FIX: Ensure the witness reflects the actual left event of THIS sequence
                 return AuditResult(
                     AuditVerdict.FAIL,
                     operator="sequence",
                     error_code="V_SEQ_MISSING_RIGHT",
                     clause_path=path,
                     responsible_agent=res_right.responsible_agent,
                     expected={"right": "Present after left", "object": node.right.object if hasattr(node.right, "object") else None},
                     observed={"after_left_until": trace[-1].t if len(trace) > 0 else 0.0},
                     witness={"left_event": res_left.witness}
                 )
             return res_right

        right_idx = res_right.witness["idx"]
        right_t = self._get_start_time(res_right.witness)
        right_agent = self._get_agent(res_right.witness)

        # 3. Check Latency
        if node.latency:
             dt = right_t - left_t
             limit_ms = node.latency.value_ms

             if limit_ms is not None:
                 limit_sec = limit_ms / 1000.0
                 if dt > limit_sec + 1e-6:
                     return AuditResult(
                         AuditVerdict.FAIL,
                         operator="sequence",
                         error_code="V_SEQ_LATENCY_EXCEEDED",
                         clause_path=path,
                         budget=f"≤{limit_sec}s",
                         responsible_agent=right_agent,
                         expected={"latency_leq": f"{limit_sec}s"},
                         observed={"dt": dt},
                         witness={"left_event": res_left.witness, "right_event": res_right.witness}
                     )

        # PASS
        return AuditResult(
            AuditVerdict.PASS,
            witness={"left": res_left.witness, "right": res_right.witness, "idx": right_idx}
        )

    def _check_par(self, node: Par, trace: Trace, start_idx: int, path: str) -> AuditResult:
        res_left = self._check_node(node.left, trace, start_idx, path + ".left")
        if res_left.verdict == AuditVerdict.FAIL:
             return AuditResult(
                 AuditVerdict.FAIL,
                 operator="parallel",
                 error_code="V_PAR_MISSING_LEFT",
                 clause_path=path,
                 responsible_agent=res_left.responsible_agent,
                 expected={"left": "Present"},
                 observed={"searched_from": start_idx}
             )
             
        res_right = self._check_node(node.right, trace, start_idx, path + ".right")
        if res_right.verdict == AuditVerdict.FAIL:
             return AuditResult(
                 AuditVerdict.FAIL,
                 operator="parallel",
                 error_code="V_PAR_MISSING_RIGHT",
                 clause_path=path,
                 responsible_agent=res_right.responsible_agent,
                 expected={"right": "Present"},
                 observed={"searched_from": start_idx}
             )

        # Get timestamps
        t_left = self._get_start_time(res_left.witness)
        t_right = self._get_start_time(res_right.witness)
        
        agent_left = self._get_agent(res_left.witness)
        agent_right = self._get_agent(res_right.witness)

        # Check Sync (Start)
        if node.sync and "start" in node.sync:
            sync_constraint = node.sync["start"]
            limit_ms = sync_constraint.value_ms
            
            if limit_ms is not None:
                limit_sec = limit_ms / 1000.0
                diff = abs(t_left - t_right)
                
                if diff > limit_sec + 1e-6:
                     # Blame the later agent
                     bad_agent = agent_right if t_right > t_left else agent_left
                     
                     return AuditResult(
                         AuditVerdict.FAIL,
                         operator="parallel",
                         error_code="V_PAR_SYNC_START",
                         clause_path=path,
                         budget=f"sync start ≤{limit_sec}s",
                         responsible_agent=bad_agent,
                         expected={"skew_leq": f"{limit_sec}s"},
                         observed={"skew": diff},
                         witness={"left_event": res_left.witness, "right_event": res_right.witness}
                     )

        max_idx = max(res_left.witness["idx"], res_right.witness["idx"])
        return AuditResult(
            AuditVerdict.PASS,
            witness={"left": res_left.witness, "right": res_right.witness, "idx": max_idx}
        )

    def _check_repair(self, node: Repair, trace: Trace, start_idx: int, path: str) -> AuditResult:
        attempt = 0
        max_retries = node.retry.n_max if node.retry else 0
        current_start_idx = start_idx
        last_failure = None

        # Track all prompts issued by the robot for this repair site
        prompts_issued = 0

        while attempt <= max_retries:
            res = self._check_node(node.expr, trace, current_start_idx, path + ".expr")

            if res.verdict == AuditVerdict.PASS:
                # If we passed, but we did it on an attempt that exceeds the budget, it's a failure
                if attempt > max_retries:
                    return AuditResult(
                        AuditVerdict.FAIL,
                        operator="repair",
                        error_code="V_REPAIR_EXHAUSTED",
                        clause_path=path,
                        budget=f"retries ≤ {max_retries}",
                        responsible_agent=node.expr.left.agent[0] if isinstance(node.expr.left.agent, list) else str(node.expr.left.agent),
                        observed={"attempts": attempt + 1},
                        witness={"last_failure": res.to_dict()}
                    )
                return res

            last_failure = res

            # Count the prompt that was just attempted
            if "left_event" in res.witness:
                prompts_issued += 1

            attempt += 1
            if attempt > max_retries:
                # Check if the robot issued yet another prompt beyond the budget
                # Search the trace for any more prompts for this specific action
                found_extra = False
                search_idx = current_start_idx
                if "left_event" in res.witness:
                    search_idx = res.witness["left_event"].get("idx", 0) + 1

                for i in range(search_idx, len(trace)):
                    if EventMatcher.match_act(node.expr.left, trace[i]):
                        found_extra = True
                        break

                if found_extra:
                    # Robot is responsible for exceeding budget
                    return AuditResult(
                        AuditVerdict.FAIL,
                        operator="repair",
                        error_code="V_REPAIR_EXHAUSTED",
                        clause_path=path,
                        budget=f"retries ≤ {max_retries}",
                        responsible_agent=node.expr.left.agent[0] if isinstance(node.expr.left.agent, list) else str(node.expr.left.agent),
                        observed={"attempts": prompts_issued + 1},
                        witness={"last_failure": res.to_dict()}
                    )
                else:
                    # Budget not exceeded, but no more responses. Human is responsible.
                    return AuditResult(
                        AuditVerdict.FAIL,
                        operator="repair",
                        error_code="V_REPAIR_EXHAUSTED",
                        clause_path=path,
                        budget=f"retries ≤ {max_retries}",
                        responsible_agent=node.expr.right.agent[0] if isinstance(node.expr.right.agent, list) else str(node.expr.right.agent),
                        observed={"attempts": prompts_issued},
                        witness={"last_failure": res.to_dict()}
                    )

            # Advance start_idx to move past the trigger of the failed attempt
            if "left_event" in res.witness and isinstance(res.witness["left_event"], dict):
                left_idx = res.witness["left_event"].get("idx")
                if left_idx is not None:
                    current_start_idx = left_idx + 1
                else:
                    current_start_idx += 1
            else:
                current_start_idx += 1

            if current_start_idx >= len(trace):
                 break

        return last_failure if last_failure else AuditResult(AuditVerdict.FAIL)

    def _check_neg(self, node: Neg, trace: Trace, start_idx: int, path: str) -> AuditResult:
        inner = self._check_node(node.expr, trace, start_idx, path + ".expr")
        if inner.verdict == AuditVerdict.PASS:
            return AuditResult(
                AuditVerdict.FAIL,
                operator="negation",
                error_code="V_NEG_VIOLATED",
                clause_path=path,
                expected={"negated_expr": "should NOT match"},
                observed={"matched": True},
                witness=inner.witness,
            )
        return AuditResult(AuditVerdict.PASS, witness={"neg": True, "idx": start_idx})

    def _check_bind(self, node: Bind, trace: Trace, start_idx: int, path: str) -> AuditResult:
        results = []
        for i, item in enumerate(node.items):
            r = self._check_node(item, trace, start_idx, f"{path}.items[{i}]")
            if r.verdict == AuditVerdict.FAIL:
                return r
            results.append(r)

        timestamps = []
        for r in results:
             timestamps.extend(self._get_all_times(r.witness))

        max_idx = max((r.witness.get("idx", -1) for r in results), default=-1)

        if node.latency and timestamps:
            span = max(timestamps) - min(timestamps)
            limit_ms = node.latency.value_ms
            if limit_ms is not None:
                limit_sec = limit_ms / 1000.0
                if span > limit_sec + 1e-6:
                    return AuditResult(
                        AuditVerdict.FAIL,
                        operator="bind",
                        error_code="V_BIND_LATENCY_EXCEEDED",
                        clause_path=path,
                        budget=f"≤{limit_sec}s",
                        observed={"span": span},
                        witness={"items": [r.witness for r in results]},
                    )

        return AuditResult(
            AuditVerdict.PASS,
            witness={"items": [r.witness for r in results], "idx": max_idx}
        )

    def _get_start_time(self, witness: Dict) -> float:
        times = []
        if "t" in witness: times.append(witness["t"])
        if "idx" in witness and "event" in witness and isinstance(witness["event"], dict):
             if "t" in witness["event"]: times.append(witness["event"]["t"])
             
        if "left" in witness: times.append(self._get_start_time(witness["left"]))
        if "right" in witness: times.append(self._get_start_time(witness["right"]))
        if "items" in witness:
            for item in witness["items"]:
                times.append(self._get_start_time(item))
                
        if "left_event" in witness and isinstance(witness["left_event"], dict):
             # This might be just the dict without nesting methods, so check 't' directly
             if "t" in witness["left_event"]: times.append(witness["left_event"]["t"])
        
        if times:
            return min(times)
        return 0.0

    def _get_agent(self, witness: Dict) -> str:
        if "agent" in witness: return witness["agent"]
        if "event" in witness and isinstance(witness["event"], dict):
             return witness["event"].get("agent", "unknown")
        
        # Priority search
        if "left" in witness: 
            a = self._get_agent(witness["left"])
            if a != "unknown": return a
        if "right" in witness: 
            a = self._get_agent(witness["right"])
            if a != "unknown": return a
        if "items" in witness:
             for item in witness["items"]:
                 a = self._get_agent(item)
                 if a != "unknown": return a
        return "unknown"

    def _get_all_times(self, witness: Dict) -> List[float]:
        times = []
        if "t" in witness: times.append(witness["t"])
        if "idx" in witness and "event" in witness and isinstance(witness["event"], dict):
             if "t" in witness["event"]: times.append(witness["event"]["t"])
             
        if "left" in witness: times.extend(self._get_all_times(witness["left"]))
        if "right" in witness: times.extend(self._get_all_times(witness["right"]))
        if "items" in witness:
            for item in witness["items"]:
                times.extend(self._get_all_times(item))
                
        if "left_event" in witness and isinstance(witness["left_event"], dict):
             if "t" in witness["left_event"]: times.append(witness["left_event"]["t"])
        if "right_event" in witness and isinstance(witness["right_event"], dict):
             if "t" in witness["right_event"]: times.append(witness["right_event"]["t"])
             
        return times

    def _extract_event_data(self, witness: Dict) -> Optional[Dict]:
         if "event" in witness and isinstance(witness["event"], dict):
             return witness["event"]
         return None

def audit(contract: ASTNode, trace: Trace) -> AuditResult:
    """
    Top-level API function to audit a trace against a contract.
    Complies with API requirements.
    """
    return Auditor(contract).audit(trace)
