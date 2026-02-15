
import unittest
import logging
import json
from src.compiler.ast import Act, Seq, Par, Repair, Bind
from src.compiler.constraint_parser import LatencyConstraint, SyncConstraint, RetryConstraint
from src.audit.trace import Trace, Event
from src.audit.auditor import Auditor, AuditVerdict, AuditResult

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestAuditorPhase3(unittest.TestCase):
    def test_seq_latency_fail(self):
        logger.info("Testing Sequence Latency Failure...")
        # A -> B [<= 1s]
        a = Act(prim="σ", agent="h", channel="c")
        b = Act(prim="ρ", agent="r", channel="c")
        seq = Seq(a, b, latency=LatencyConstraint(value_ms=1000.0))
        
        events = [
            Event(t=1.0, prim="σ", agent="h", channel="c"),
            Event(t=3.0, prim="ρ", agent="r", channel="c") # dt=2.0
        ]
        trace = Trace(events)
        
        res = Auditor(seq).audit(trace)
        logger.info(f"Verdict: {res.verdict}, Error: {res.error_code}, Observed dt: {res.observed.get('dt')}")
        
        self.assertEqual(res.verdict, AuditVerdict.FAIL)
        self.assertEqual(res.error_code, "V_SEQ_LATENCY_EXCEEDED")
        self.assertEqual(res.budget, "≤1.0s")
        # dt check: numeric approximate
        self.assertAlmostEqual(res.observed["dt"], 2.0)

    def test_par_sync_fail(self):
        logger.info("Testing Parallel Sync Failure...")
        # A || B [sync start <= 0.5s]
        a = Act(prim="σ", agent="h", channel="c", object="A")
        b = Act(prim="ρ", agent="r", channel="c", object="B")
        par = Par(a, b, sync={"start": SyncConstraint(value_ms=500.0, type="start")})
        
        events = [
            Event(t=1.0, prim="σ", agent="h", channel="c", object="A"),
            Event(t=2.0, prim="ρ", agent="r", channel="c", object="B") # diff=1.0
        ]
        trace = Trace(events)
        
        res = Auditor(par).audit(trace)
        logger.info(f"Verdict: {res.verdict}, Error: {res.error_code}, Observed skew: {res.observed.get('skew')}")

        self.assertEqual(res.verdict, AuditVerdict.FAIL)
        self.assertEqual(res.error_code, "V_PAR_SYNC_START")
        self.assertAlmostEqual(res.observed["skew"], 1.0)

    def test_repair_success(self):
        logger.info("Testing Repair Success...")
        # repair(site="X", retry={N<=1}, seq(A, B [<= 1s]))
        # Trace: A1(1.0), B1(3.0) [Fail], A2(5.0), B2(5.5) [Pass]
        
        a = Act(prim="σ", agent="h", channel="c")
        b = Act(prim="ρ", agent="r", channel="c")
        inner = Seq(a, b, latency=LatencyConstraint(value_ms=1000.0))
        repair = Repair(site="X", expr=inner, retry=RetryConstraint(n_max=1))
        
        events = [
            Event(t=1.0, prim="σ", agent="h", channel="c"),
            Event(t=3.0, prim="ρ", agent="r", channel="c"), # Fail (dt=2.0)
            Event(t=5.0, prim="σ", agent="h", channel="c"),
            Event(t=5.5, prim="ρ", agent="r", channel="c")  # Pass (dt=0.5)
        ]
        trace = Trace(events)
        
        res = Auditor(repair).audit(trace)
        logger.info(f"Verdict: {res.verdict}")
        if res.verdict == AuditVerdict.FAIL:
             logger.error(f"Failed with: {res.to_dict()}")

        self.assertEqual(res.verdict, AuditVerdict.PASS)
        
        # Verify witness points to the second attempt events
        left_t = res.witness["left"]["event"]["t"]
        self.assertEqual(left_t, 5.0)

    def test_repair_exhausted(self):
        logger.info("Testing Repair Exhausted...")
        # repair(..., retry={N<=1}, ...)
        # Trace: A1(1.0), B1(3.0) [Fail], A2(5.0), B2(7.0) [Fail]
        a = Act(prim="σ", agent="h", channel="c")
        b = Act(prim="ρ", agent="r", channel="c")
        inner = Seq(a, b, latency=LatencyConstraint(value_ms=1000.0))
        repair = Repair(site="X", expr=inner, retry=RetryConstraint(n_max=1))
        
        events = [
            Event(t=1.0, prim="σ", agent="h", channel="c"),
            Event(t=3.0, prim="ρ", agent="r", channel="c"),
            Event(t=5.0, prim="σ", agent="h", channel="c"),
            Event(t=7.0, prim="ρ", agent="r", channel="c")
        ]
        trace = Trace(events)
        
        res = Auditor(repair).audit(trace)
        logger.info(f"Verdict: {res.verdict}, Error: {res.error_code}, Attempts: {res.observed.get('attempts')}")
        
        self.assertEqual(res.verdict, AuditVerdict.FAIL)
        self.assertEqual(res.error_code, "V_REPAIR_EXHAUSTED")
        self.assertEqual(res.observed["attempts"], 2)

    def test_nested_structure(self):
        logger.info("Testing Nested Structure...")
        # seq(A, par(B, C))
        a = Act(prim="σ", agent="h", channel="c", object="A")
        b = Act(prim="σ", agent="h", channel="c", object="B")
        c = Act(prim="σ", agent="h", channel="c", object="C")
        
        # A then (B || C)
        structure = Seq(a, Par(b, c))
        
        events = [
            Event(t=1.0, prim="σ", agent="h", channel="c", object="A"),
            Event(t=2.0, prim="σ", agent="h", channel="c", object="B"),
            Event(t=2.0, prim="σ", agent="h", channel="c", object="C")
        ]
        trace = Trace(events)
        
        res = Auditor(structure).audit(trace)
        logger.info(f"Verdict: {res.verdict}")
        
        self.assertEqual(res.verdict, AuditVerdict.PASS)

    def test_determinism(self):
        logger.info("Testing Determinism...")
        # Regression test: Same trace → 10 runs → identical result object
        a = Act(prim="σ", agent="h", channel="c")
        b = Act(prim="ρ", agent="r", channel="c")
        seq = Seq(a, b, latency=LatencyConstraint(value_ms=1000.0))
        
        # Trace with failure
        events = [
            Event(t=1.0, prim="σ", agent="h", channel="c"),
            Event(t=3.0, prim="ρ", agent="r", channel="c") 
        ]
        trace = Trace(events)
        
        results = []
        for i in range(10):
            results.append(Auditor(seq).audit(trace).to_dict())
            
        first = results[0]
        for i in range(1, 10):
            self.assertEqual(results[i], first, f"Run {i} differs from run 0")
        logger.info("Determinism check passed: 10/10 runs identical.")

if __name__ == '__main__':
    unittest.main()
