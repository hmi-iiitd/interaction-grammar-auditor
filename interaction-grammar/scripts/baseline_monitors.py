import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load scenario matrix to know what the baselines should actually check
# In a real run, we'd load the actual matrix from the dataset_nao folder
SCENARIO_MATRIX = [
    {"id": "A1_delivery_success", "expected": "SAT", "type": "none"},
    {"id": "A2_recipient_does_not_acknowledge", "expected": "UNSAT", "type": "missing_ack"},
    {"id": "A3_recipient_acknowledges_too_late", "expected": "UNSAT", "type": "late_ack"},
    {"id": "A4_robot_does_not_confirm_delivery", "expected": "UNSAT", "type": "missing_robot_confirm"},
    {"id": "B1_human_interrupts_robot_stops", "expected": "SAT", "type": "none"},
    {"id": "B2_human_interrupts_robot_continues", "expected": "UNSAT", "type": "interruption"},
    {"id": "B3_robot_interrupts_human", "expected": "UNSAT", "type": "robot_interruption"},
    {"id": "B4_robot_stops_but_no_sorry", "expected": "UNSAT", "type": "missing_interrupt_ack"},
    {"id": "C1_retry_success", "expected": "SAT", "type": "none"},
    {"id": "C2_repair_exhausted", "expected": "UNSAT", "type": "repair_exhausted"},
    {"id": "C3_retry_limit_exceeded", "expected": "UNSAT", "type": "retry_limit_exceeded"},
    {"id": "C4_global_timeout", "expected": "UNSAT", "type": "global_timeout"},
]

class BaseMonitor:
    def audit(self, scenario_id: str, trace: List[Dict]) -> Dict[str, Any]:
        raise NotImplementedError

class TaskOutcomeMonitor(BaseMonitor):
    """Baseline 1: Only checks if the interaction reached the 'expected' end state."""
    def audit(self, scenario_id: str, trace: List[Dict]) -> Dict[str, Any]:
        # Very simple: did it end with a confirmation?
        if not trace:
            return {"verdict": "UNSAT", "reason": "Empty trace"}

        last_event = trace[-1]
        # Check if the last event is a confirmation or successful end
        if "confirm" in last_event.get("object", "").lower() or "end" in last_event.get("object", "").lower():
            return {"verdict": "SAT", "reason": "Task completed"}

        return {"verdict": "UNSAT", "reason": "Task did not reach final state"}

class RuleBasedMonitor(BaseMonitor):
    """Baseline 2: Hand-coded if-else rules for the 12 scenarios."""
    def audit(self, scenario_id: str, trace: List[Dict]) -> Dict[str, Any]:
        # We implement a set of generic rules that a non-expert would likely write
        # instead of a formal contract.

        events = trace

        # 1. Check for Delivery Family (A)
        if scenario_id.startswith("A"):
            # Rule: Robot announce -> Human Ack (<= 8s) -> Robot Confirm (<= 1s)
            announce = next((e for e in events if "announce" in e.get("object", "").lower()), None)
            ack = next((e for e in events if "ack" in e.get("object", "").lower()), None)
            confirm = next((e for e in events if "confirm" in e.get("object", "").lower()), None)

            if not announce: return {"verdict": "UNSAT", "reason": "missing_announce"}
            if not ack: return {"verdict": "UNSAT", "reason": "missing_ack"}
            if ack["t"] - announce["t"] > 8.0: return {"verdict": "UNSAT", "reason": "late_ack"}
            if not confirm: return {"verdict": "UNSAT", "reason": "missing_confirm"}
            if confirm["t"] - ack["t"] > 1.0: return {"verdict": "UNSAT", "reason": "late_confirm"}
            return {"verdict": "SAT", "reason": "Rules passed"}

        # 2. Check for Interruption Family (B)
        if scenario_id.startswith("B"):
            # Rule: If human speaks and robot also speaks, robot must stop
            speaking_start = next((e for e in events if e.get("prim") == "σ"), None)
            speaking_end = next((e for e in events if e.get("prim") == "ρ"), None)

            if speaking_start and speaking_end:
                # Check if robot did something during this window
                for e in events:
                    if speaking_start["t"] < e["t"] < speaking_end["t"] and e["agent"] == "robot_1":
                        # Robot spoke while human was speaking
                        return {"verdict": "UNSAT", "reason": "interruption_detected"}
            return {"verdict": "SAT", "reason": "No interruption rules broken"}

        # 3. Check for Repair Family (C)
        if scenario_id.startswith("C"):
            # Rule: Count how many times a specific prompt was repeated
            prompts = [e for e in events if "prompt" in e.get("object", "").lower()]
            if len(prompts) > 3: # Arbitrary limit for baseline
                return {"verdict": "UNSAT", "reason": "too_many_retries"}
            return {"verdict": "SAT", "reason": "Repair count OK"}

        return {"verdict": "UNSAT", "reason": "Scenario family not recognized"}

class FSMMonitor(BaseMonitor):
    """Baseline 3: Simple state machine tracker."""
    def audit(self, scenario_id: str, trace: List[Dict]) -> Dict[str, Any]:
        state = "IDLE"

        for e in trace:
            obj = e.get("object", "").lower()
            agent = e.get("agent", "")

            # Family A logic
            if "announce" in obj and agent == "robot_1":
                state = "ANNOUNCED"
            elif "ack" in obj and agent == "human_1" and state == "ANNOUNCED":
                state = "ACKED"
            elif "confirm" in obj and agent == "robot_1" and state == "ACKED":
                state = "DONE"

            # Family B logic
            elif e.get("prim") == "σ" and agent == "human_1":
                state = "HUMAN_SPEAKING"
            elif e.get("prim") == "ρ" and agent == "human_1":
                state = "IDLE"
            elif agent == "robot_1" and state == "HUMAN_SPEAKING":
                return {"verdict": "UNSAT", "reason": "fsm_interruption"}

        if state == "DONE":
            return {"verdict": "SAT", "reason": "FSM reached final state"}
        return {"verdict": "UNSAT", "reason": f"FSM stopped at {state}"}

if __name__ == "__main__":
    # Quick test
    sample_trace = [
        {"t": 0.0, "prim": "α", "agent": "robot_1", "channel": "speech", "object": "delivery announce"},
        {"t": 2.0, "prim": "α", "agent": "human_1", "channel": "speech", "object": "ack"},
        {"t": 3.0, "prim": "α", "agent": "robot_1", "channel": "speech", "object": "confirm"},
    ]

    print("Testing A1 with baselines...")
    print(f"Outcome: {TaskOutcomeMonitor().audit('A1', sample_trace)}")
    print(f"Rule-Based: {RuleBasedMonitor().audit('A1', sample_trace)}")
    print(f"FSM: {FSMMonitor().audit('A1', sample_trace)}")
