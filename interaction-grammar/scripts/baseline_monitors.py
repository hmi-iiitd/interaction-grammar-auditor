import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load scenario matrix to know what the baselines should actually check
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
    """Baseline 1: Checks if the interaction reached the desired goal state."""
    def audit(self, scenario_id: str, trace: List[Dict]) -> Dict[str, Any]:
        if not trace:
            return {"verdict": "UNSAT", "reason": "Empty trace"}

        # Success indicators for all families
        success_indicators = [
            "confirm",               # A-family: Robot confirms delivery
            "stops_speaking",        # B-family: Robot successfully stops
            "responds_to_prompt",    # C-family: User finally responds
            "acknowledges_intent"    # C-family: User acknowledges intent
        ]

        for event in trace:
            obj = event.get("object", "").lower()
            if any(keyword in obj for keyword in success_indicators):
                return {"verdict": "SAT", "reason": "Goal state reached"}

        return {"verdict": "UNSAT", "reason": "Task did not reach goal state"}

class RuleBasedMonitor(BaseMonitor):
    """Baseline 2: Hand-coded if-else rules for the 12 scenarios."""
    def audit(self, scenario_id: str, trace: List[Dict]) -> Dict[str, Any]:
        events = trace

        if scenario_id.startswith("A"):
            announce = next((e for e in events if "announce" in e.get("object", "").lower()), None)
            ack = next((e for e in events if "ack" in e.get("object", "").lower()), None)
            confirm = next((e for e in events if "confirm" in e.get("object", "").lower()), None)

            if not announce: return {"verdict": "UNSAT", "reason": "missing_announce"}
            if not ack: return {"verdict": "UNSAT", "reason": "missing_ack"}
            if ack["t"] - announce["t"] > 8.0: return {"verdict": "UNSAT", "reason": "late_ack"}
            if not confirm: return {"verdict": "UNSAT", "reason": "missing_confirm"}
            if confirm["t"] - ack["t"] > 1.0: return {"verdict": "UNSAT", "reason": "late_confirm"}
            return {"verdict": "SAT", "reason": "Rules passed"}

        if scenario_id.startswith("B"):
            speaking_start = next((e for e in events if e.get("prim") == "σ"), None)
            speaking_end = next((e for e in events if e.get("prim") == "ρ"), None)

            if speaking_start and speaking_end:
                for e in events:
                    if speaking_start["t"] < e["t"] < speaking_end["t"] and e["agent"] == "robot_1":
                        return {"verdict": "UNSAT", "reason": "interruption_detected"}
            return {"verdict": "SAT", "reason": "No interruption rules broken"}

        if scenario_id.startswith("C"):
            prompts = [e for e in events if "prompt" in e.get("object", "").lower()]
            if len(prompts) > 3:
                return {"verdict": "UNSAT", "reason": "too_many_retries"}
            return {"verdict": "SAT", "reason": "Repair count OK"}

        return {"verdict": "UNSAT", "reason": "Scenario family not recognized"}

class FSMMonitor(BaseMonitor):
    """Baseline 3: Fair state machine tracker."""
    def audit(self, scenario_id: str, trace: List[Dict]) -> Dict[str, Any]:
        state = "IDLE"
        reached_done = False
        retry_count = 0

        for e in trace:
            # Filter for semantic acts only to avoid noise distraction
            if e.get("prim") != "α":
                continue

            obj = e.get("object", "").lower()
            agent = e.get("agent", "")

            # --- Family A Logic ---
            if "announce" in obj and agent == "robot_1":
                state = "ANNOUNCED"
            elif "ack" in obj and agent == "human_1" and state == "ANNOUNCED":
                state = "ACKED"
            elif "confirm" in obj and agent == "robot_1" and state == "ACKED":
                state = "DONE"
                reached_done = True

            # --- Family B Logic ---
            elif "interrupts" in obj and agent == "human_1":
                state = "HUMAN_SPEAKING"
            elif "stops" in obj and agent == "robot_1" and state == "HUMAN_SPEAKING":
                state = "B_DONE"
                reached_done = True
            elif agent == "robot_1" and state == "HUMAN_SPEAKING" and "stops" not in obj:
                # Robot spoke while human was speaking and didn't stop
                return {"verdict": "UNSAT", "reason": "fsm_interruption"}

            # --- Family C Logic ---
            elif "prompt" in obj and agent == "robot_1":
                retry_count += 1
                state = "C_WAITING"
            elif "responds" in obj and agent == "human_1" and state == "C_WAITING":
                state = "C_DONE"
                reached_done = True
            elif "acknowledges" in obj and agent == "human_1" and state == "C_WAITING":
                state = "C_DONE"
                reached_done = True

        if reached_done:
            return {"verdict": "SAT", "reason": "FSM reached final state"}

        return {"verdict": "UNSAT", "reason": f"FSM stopped at {state}"}

if __name__ == "__main__":
    sample_trace = [
        {"t": 0.0, "prim": "α", "agent": "robot_1", "channel": "speech", "object": "delivery announce"},
        {"t": 2.0, "prim": "α", "agent": "human_1", "channel": "speech", "object": "ack"},
        {"t": 3.0, "prim": "α", "agent": "robot_1", "channel": "speech", "object": "confirm"},
    ]
    print("Testing A1 with baselines...")
    print(f"Outcome: {TaskOutcomeMonitor().audit('A1', sample_trace)}")
    print(f"Rule-Based: {RuleBasedMonitor().audit('A1', sample_trace)}")
    print(f"FSM: {FSMMonitor().audit('A1', sample_trace)}")
