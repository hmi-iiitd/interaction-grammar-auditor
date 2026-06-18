# Pilot User Study Protocol: Interaction Contract Auditor

## 1. Objective
The goal of this pilot study is to evaluate whether the Interaction Contract authoring and auditing interface helps non-technical HRI researchers:
1. Formulate interaction contracts from natural language.
2. Diagnose interaction failures using counterexamples.

## 2. Participants
- **N:** 3–5 participants.
- **Profile:** HRI students, Psychology/Cognitive Science students, or Design researchers. (Non-formal methods experts).

## 3. Study Design (Within-Subjects)

### Part A: Contract Authoring
**Task:** Create an auditable contract for a specific NAO scenario.
- **Condition 1 (Template):** User fills a structured JSON/Form manually.
- **Condition 2 (Assisted):** User uses the NL $\rightarrow$ Clarification $\rightarrow$ Lock pipeline.

**Metrics:**
- Time to reach a `VALID` contract.
- Number of validation errors encountered.
- User confidence rating (1-5).

### Part B: Failure Diagnosis
**Task:** Given a trace and a la contract, identify exactly what went wrong.
- **Condition 1 (Raw):** User sees the raw trace/timeline.
- **Condition 2 (Audit):** User sees the `audit_report.json` and `counterexample.json`.
- **Condition 3 (Audit+LLM):** User sees the report and a grounded natural language explanation.

**Metrics:**
- Diagnosis Accuracy: Did they find the correct failure type?
- Timestamp Accuracy: How close was their guess to the actual falsification time?
- Time to Diagnosis (seconds).

## 4. Procedural Flow
1. **Onboarding:** Briefly explain the concept of an "Interaction Contract."
2. **Authoring Phase:** Run Part A for two scenarios (e.g., A1 and B3).
3. **Diagnosis Phase:** Run Part B for four failure cases (e.g., A2, B2, C2, C4).
4. **Exit Interview:** Administer SUS (System Usability Scale) and NASA-TLX.

## 5. Analysis
Compare the a-priori ground truth for the scenarios against the participant's findings to calculate Precision and Recall of the diagnosis process.
