# NAO Scenario Matrix

This matrix defines the ground truth expectations for the 12 scenarios used to evaluate the Interaction Contract Auditor.

| ID | Scenario | Family | Expected Verdict | Failure Type | Trigger Event | Expected Event | Deadline |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **A1** | Normal Delivery | Delivery | SAT | None | Robot Announce | Human Ack $\rightarrow$ Robot Confirm | Ack $\le$ 8s |
| **A2** | Missing Ack | Delivery | UNSAT | `missing_ack` | Robot Announce | Human Acknowledgment | 8s |
| **A3** | Late Ack | Delivery | UNSAT | `late_ack` | Robot Announce | Human Acknowledgment | 8s |
| **A4** | Missing Confirm | Delivery | UNSAT | `missing_robot_confirm` | Human Ack | Robot Confirmation | 1s |
| **B1** | Correct Interruption | Interruption | SAT | None | Human Interruption | Robot Stop $\rightarrow$ Ack | 1s |
| **B2** | Robot Continues | Interruption | UNSAT | `interruption` | Human Interruption | Robot Speaking End | 1s |
| **B3** | Robot Interrupts | Interruption | UNSAT | `robot_interruption` | Human Start | Robot Silence | Duration |
| **B4** | No Sorry | Interruption | UNSAT | `missing_interrupt_ack` | Robot Stop | Robot "Sorry" | 1s |
| **C1** | Repair Success | Repair | SAT | None | Robot Prompt | Human Ack (after retry) | $\le$ 1 Retry |
| **C2** | Repair Exhausted | Repair | UNSAT | `repair_exhausted` | Retry Prompt | Human Acknowledgment | 3s |
| **C3** | Retry Exceeded | Repair | UNSAT | `retry_limit_exceeded` | 2nd Retry | No more retries | $\le$ 1 Retry |
| **C4** | Global Timeout | Repair | UNSAT | `global_timeout` | Interaction Start | Interaction Completion | 5s |
