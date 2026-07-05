# Reproducibility Report

The following table shows the consistency of audit verdicts across three independent runs.

| Scenario | Run 1 | Run 2 | Run 3 | Result |
| :--- | :---: | :---: | :---: | :---: |
| A1_delivery_success | PASS | PASS | PASS | YES |
| A2_recipient_does_not_acknowledge | FAIL | FAIL | FAIL | YES |
| A3_recipient_acknowledges_too_late | FAIL | FAIL | FAIL | YES |
| A4_robot_does_not_confirm_delivery | FAIL | FAIL | FAIL | YES |
| B1_human_interrupts_robot_stops | PASS | PASS | PASS | YES |
| B2_human_interrupts_robot_continues | FAIL | FAIL | FAIL | YES |
| B3_robot_interrupts_human | FAIL | FAIL | FAIL | YES |
| B4_robot_stops_but_no_sorry | FAIL | FAIL | FAIL | YES |
| C1_retry_success | PASS | PASS | PASS | YES |
| C2_repair_exhausted | FAIL | FAIL | FAIL | YES |
| C3_retry_limit_exceeded | FAIL | FAIL | FAIL | YES |
| C4_global_timeout | FAIL | FAIL | FAIL | YES |
