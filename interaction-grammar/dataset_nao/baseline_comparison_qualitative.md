# Baseline Comparison: Qualitative Analysis

This table compares the Interaction Auditor against three common HRI monitoring baselines across a set of diagnostic capabilities.

| Metric | Task Outcome | Rule Monitor | FSM Monitor | Interaction Auditor |
| :--- | :---: | :---: | :---: | :---: |
| **Detects Failure** | 🟡 | 🟡 | 🟡 | ✅ |
| **Identifies Failure Type** | ❌ | 🟡 (Partial) | 🟡 (Partial) | ✅ |
| **Gives Timestamp** | ❌ | 🟡 (Maybe) | 🟡 (Maybe) | ✅ |
| **Gives Trigger Event** | ❌ | 🟡 (Maybe) | 🟡 (Maybe) | ✅ |
| **Gives Missing Expected Event** | ❌ | 🟡 (Maybe) | 🟡 (Maybe) | ✅ |
| **Gives Agent/Site Attribution** | ❌ | ❌ | 🟡 (Partial) | ✅ |
| **Reusable Contract** | ❌ | ❌ | 🟡 (Limited) | ✅ |
| **Locked Before Audit** | ❌ | ❌ | ❌ | ✅ |
| **Human-Readable Report** | ❌ | ❌ | 🟡 (Limited) | ✅ |

### Analysis of Baseline Limitations

1.  **Task Outcome Monitor:** Only tracks if the "goal" (e.g., delivery complete) was reached. It is blind to *how* it was reached and misses all coordination failures that don't prevent the final state (e.g., B2 where robot continues but eventually stops).
2.  **Rule-Based Monitor:** Uses a set of independent `if-then` rules. While it can catch simple timeouts, it lacks a global state. It cannot handle complex "Repair" patterns (like counting retries across a window) without writing exponentially complex rules. It provides a reason string but no formal evidence.
3.  **FSM Monitor:** Encodes a strict sequence of states. It is highly brittle; any unexpected event (even if harmless) causes the monitor to enter a failure state. It cannot easily express "soft" constraints like "Robot should stop *eventually* within 1s" without a massive state explosion.
4.  **Interaction Auditor:** By using a formal grammar with temporal operators, the Auditor provides a mathematically sound proof of failure. The **Locking** mechanism ensures that the "ground truth" was defined *before* seeing the data, preventing the "overfitting" common in manual rule-writing.
