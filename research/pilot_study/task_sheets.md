# Participant Task Sheets

## Task 1: Authoring a "Delivery Confirmation" Scenario
**Description:** 
"The robot announces it has a package. The human should acknowledge the delivery within 8 seconds. Then the robot should confirm and end the interaction."

**Instructions:**
- Use the authoring interface to create this contract.
- Ensure all timings are explicitly clarified.
- Lock the contract before finishing.

---

## Task 2: Authoring an "Interruption" Scenario
**Description:**
"The robot is explaining a task. If the human starts speaking, the robot must stop immediately and acknowledge the interruption. The robot should not continue its original speech while the human is talking."

**Instructions:**
- Define the 'Interruption' rule using the negation/guard constructs.
- Lock the contract.

---

## Task 3: Diagnosing Failure A2 (Missing Acknowledgment)
**Input:** You are provided with a trace and a contract.
**Question:** 
1. Did the interaction satisfy the contract?
2. If not, what exactly failed?
3. At what timestamp did the failure occur?
4. Who was responsible for the failure?

---

## Task 4: Diagnosing Failure B3 (Robot Interruption)
**Input:** You are provided with a trace and a contract.
**Question:**
1. Identify the event that caused the contract to fail.
2. Does the evidence clearly show the robot spoke while the human was speaking?
3. What would be the fix for this behavior?
