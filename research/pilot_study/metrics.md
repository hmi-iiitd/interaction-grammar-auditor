# Evaluation Metrics & Scoring Rubric

## 1. Authoring Metrics
| Metric | Definition | Scoring |
| :--- | :--- | :--- |
| **Time to Valid** | Seconds from start to `Lock` | Continuous (s) |
| **Validation Errors** | Count of failed `validate` calls | Integer |
| **Correctness** | Expert rating of the final AST | 0 (Wrong) / 1 (Correct) |
| **Confidence** | "How confident are you that this contract is correct?" | 1-5 Likert Scale |

## 2. Diagnosis Metrics
| Metric | Definition | Scoring |
| :--- | :--- | :--- |
| **Verdict Accuracy** | Did the user correctly identify SAT vs UNSAT? | Binary (0/1) |
| **Failure Site** | Did they identify the correct obligation? | Binary (0/1) |
| **Timestamp Error** | $|t_{user} - t_{actual}|$ | Continuous (s) |
| **Attribution** | Did they blame the correct agent? | Binary (0/1) |
| **Time to Diagnose** | Time from opening report to final answer | Continuous (s) |

## 3. Usability (SUS)
Administer the 10-item System Usability Scale (SUS). 
- Score = $\sum(\text{odd items}) + \sum(5 - \text{even items}) \times 2.5$
- Target: $> 68$ (Above average).
