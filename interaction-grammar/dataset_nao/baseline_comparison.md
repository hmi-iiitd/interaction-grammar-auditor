| Scenario | Auditor | Task Outcome | Rule Monitor | FSM Monitor |
| :--- | :---: | :---: | :---: | :---: |
| A1_delivery_success | PASS | SAT | SAT | UNSAT |
| A2_recipient_does_not_acknowledge | FAIL | UNSAT | UNSAT | UNSAT |
| A3_recipient_acknowledges_too_late | FAIL | UNSAT | UNSAT | UNSAT |
| A4_robot_does_not_confirm_delivery | FAIL | UNSAT | UNSAT | UNSAT |
| B1_human_interrupts_robot_stops | PASS | UNSAT | SAT | UNSAT |
| B2_human_interrupts_robot_continues | FAIL | UNSAT | SAT | UNSAT |
| B3_robot_interrupts_human | FAIL | UNSAT | UNSAT | UNSAT |
| B4_robot_stops_but_no_sorry | FAIL | UNSAT | SAT | UNSAT |
| C1_retry_success | PASS | UNSAT | SAT | UNSAT |
| C2_repair_exhausted | FAIL | UNSAT | SAT | UNSAT |
| C3_retry_limit_exceeded | FAIL | UNSAT | UNSAT | UNSAT |
| C4_global_timeout | FAIL | UNSAT | SAT | UNSAT |