
import time
import unittest
import random
import logging
from src.compiler.ast import Act, Seq, Par
from src.audit.trace import Trace, Event
from src.audit.auditor import Auditor, AuditVerdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestAuditorStress(unittest.TestCase):
    def test_stress_performance(self):
        logger.info("Starting Stress Test...")
        # 1. Create a deep contract (10 nested levels)
        # Nested Seq: A0 -> A1 -> ... -> A9
        # Or A0 -> (A1 -> ... )
        
        # Let's clean build a chain of 10 events
        root = Act(prim="σ", agent="h", channel="c", object="obj_9")
        for i in range(8, -1, -1):
            next_node = root
            root = Seq(left=Act(prim="σ", agent="h", channel="c", object=f"obj_{i}"), 
                       right=next_node)
            
        # 2. Create synthetic trace with 1000 events
        # Embed the matching events amidst noise
        events = []
        target_indices = sorted(random.sample(range(1000), 10))
        
        target_map = {idx: i for i, idx in enumerate(target_indices)}
        
        for i in range(1000):
            t = float(i) * 0.1
            if i in target_map:
                obj_id = target_map[i]
                events.append(Event(t=t, prim="σ", agent="h", channel="c", object=f"obj_{obj_id}"))
            else:
                events.append(Event(t=t, prim="noise", agent="env", channel="debug"))
                
        trace = Trace(events)
        logger.info(f"Generated trace with {len(trace)} events.")
        
        # 3. Measure runtime
        start_time = time.time()
        res = Auditor(root).audit(trace)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        logger.info(f"Stress Test Duration: {duration_ms:.2f} ms")
        
        self.assertEqual(res.verdict, AuditVerdict.PASS)
        self.assertLess(duration_ms, 50.0, "Performance requirement not met (<50ms)")

if __name__ == '__main__':
    unittest.main()
