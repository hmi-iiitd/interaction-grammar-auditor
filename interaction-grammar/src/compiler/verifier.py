from z3 import *
from .ast import ASTNode, Seq, Par, Repair, Act, Bind
from .constraint_parser import LatencyConstraint

class ContractVerifier:
    def __init__(self):
        self.solver = Solver()
        self.solver.set(unsat_core=True)

    def verify(self, ast: ASTNode) -> tuple[bool, str]:
        self.solver.reset()
        
        # Create Z3 variables for start/end times of the root
        t_start = Real('root_start')
        t_end = Real('root_end')
        
        # Basic constraint: time moves forward
        self.solver.assert_and_track(t_end >= t_start, "root_duration_positive")
        self.solver.assert_and_track(t_start >= 0, "root_start_nonneg")

        # Recursively encode constraints
        self._encode(ast, t_start, t_end)

        # Check satisfiability
        result = self.solver.check()
        if result == unsat:
            core = self.solver.unsat_core()
            return False, f"Constraints are unsatisfiable. Conflict involved: {core}"
        elif result == unknown:
            return False, "Solver returned unknown."
        
        return True, "Constraints are satisfiable."

    def _encode(self, node: ASTNode, t_start, t_end):
        node_id = str(id(node))
        if isinstance(node, Act):
            # Atomic action takes some non-negative time
            self.solver.assert_and_track(t_end >= t_start, f"act_duration_{node_id}")
        
        elif isinstance(node, Seq):
            # Sequence: left then right
            t_mid = Real(f'seq_mid_{node_id}')
            self._encode(node.left, t_start, t_mid)
            self._encode(node.right, t_mid, t_end)
            
            # Latency constraint if present
            if node.latency:
                if isinstance(node.latency, LatencyConstraint):
                    limit = node.latency.value_ms
                    self.solver.assert_and_track(t_end - t_start <= limit, f"seq_latency_{node_id}")

        elif isinstance(node, Par):
            t_l_end = Real(f'par_l_end_{node_id}')
            t_r_end = Real(f'par_r_end_{node_id}')
            
            self._encode(node.left, t_start, t_l_end)
            self._encode(node.right, t_start, t_r_end)
            
            self.solver.assert_and_track(t_end >= t_l_end, f"par_end_left_{node_id}")
            self.solver.assert_and_track(t_end >= t_r_end, f"par_end_right_{node_id}")
            
            if node.sync:
                if "start" in node.sync:
                    # For now, just a placeholder constraint to show tracking
                    # Real implementation would need start times passed down
                    pass

        elif isinstance(node, Repair):
            self._encode(node.expr, t_start, t_end)
