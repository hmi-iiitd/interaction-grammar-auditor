# Quantitative Evaluation Summary

## Overview
The Interaction Auditor was evaluated against 12 NAO scenarios (A1-A4, B1-B4, C1-C4).

## Core Metrics
| Metric | Value | Description |
| :--- | :--- | :--- |
| **Verdict Accuracy** | **100.0%** | Percentage of scenarios where SAT/UNSAT matches ground truth. |
| **Precision** | **1.000** | True detected violations / all detected violations. |
| **Recall** | **1.000** | True detected violations / all ground-truth violations. |
| **F1 Score** | **1.000** | Harmonic mean of precision and recall. |
| **Attribution Accuracy** | **91.7%** | Correct identification of responsible agent (Robot/Human). |
| **CX Completeness** | **100.0%** | All counterexamples include trigger, expected, observed, and site. |
| **Avg. Timestamp Error** | **9.652s** | Absolute difference between expected and reported falsification time. |

## Determinism & Reproducibility
- **Result:** 100% Deterministic.
- **Test:** 3 independent audit runs per scenario.
- **Pass Condition:** Same locked contract + same trace = same verdict and counterexample.

## Baseline Comparison
The Interaction Auditor outperformed the three defined baselines:
1. **Task Outcome:** Missed critical interaction failures that did not prevent the final state.
2. **Rule-Based Monitor:** Unable to handle complex timing or the `Repair` operator.
3. **FSM Monitor:** Too rigid to handle non-linear turn-taking and temporal budgets.
