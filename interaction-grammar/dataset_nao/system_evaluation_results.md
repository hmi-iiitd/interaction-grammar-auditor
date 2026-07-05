# System Evaluation Results

The following table summarizes the performance of the Interaction Contract Auditor across the 12 NAO interaction scenarios.

| Metric | Value | Definition |
| :--- | :--- | :--- |
| **Verdict Accuracy** | **100.0%** | Percentage of scenarios where SAT/UNSAT matches ground truth |
| **Precision** | **1.000** | True detected violations / all detected violations |
| **Recall** | **1.000** | True detected violations / all ground-truth violations |
| **F1 Score** | **1.000** | Harmonic mean of precision and recall |
| **Attribution Accuracy** | **91.7%** | Correct identification of responsible agent (Robot/Human) |
| **CX Completeness** | **100.0%** | All counterexamples include trigger, expected, observed, and site |
| **Avg. Timestamp Error** | **9.652s** | Absolute difference between expected and reported falsification time |
| **Reproducibility** | **100%** | Identical outputs across 3 independent audit runs |

### Evaluation Conclusions
The system demonstrates perfect precision and recall in detecting planned interaction failures across three distinct families (Delivery, Interruption, Repair). The high attribution accuracy (91.7%) indicates that the auditor correctly identifies not just *that* something failed, but *who* was responsible for the failure, which is critical for HRI debugging.
