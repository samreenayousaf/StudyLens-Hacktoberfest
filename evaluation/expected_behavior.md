# StudyLens Evaluation Specification & Qualitative Expectations

This document outlines the evaluation criteria and expected qualitative behavior for StudyLens answer analysis and mastery tracking.

## Qualitative Category Specifications

| Category | Description | Expected Score Range | Expected Misconception Behavior | Expected Retest Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **`strong`** | Complete, accurate explanation demonstrating clear conceptual mastery. | `75.0 – 100.0` | No misconceptions | No immediate retest (`required: false`) |
| **`acceptable`** | Partially complete answer containing correct core ideas but missing finer details. | `50.0 – 85.0` | No major misconceptions | Retest only if mastery falls into developing/weak |
| **`weak`** | Minimal or non-informative answer ("I don't know"). | `0.0 – 30.0` | No misconceptions required | Retest required (`required: true`) |
| **`misconception`** | Answer advocates incorrect principles (e.g. claims high coupling is desirable). | `0.0 – 50.0` | Identifies specific misconception | Retest required (`required: true`) |
| **`off_topic`** | Answer completely unrelated to the software engineering question. | `0.0 – 30.0` | No concept credit | Retest required (`required: true`) |

## Evaluation Metrics

1. **Schema Validity**:
   - `understanding_score` is a numeric float in range `[0.0, 100.0]`.
   - `detected_concepts` is a list of valid active curriculum concepts.
   - `misconceptions` is a list of string descriptions.
   - `evidence` is a non-empty string explanation.
2. **Coupling False-Positive Rate**:
   - Explanations supporting low coupling or identifying high coupling as undesirable must **NOT** trigger a false "high coupling preference" misconception.
3. **Mastery Engine Integrity**:
   - Scores clamped between `0.0` and `100.0`.
   - Level mapping: `weak` (0–39), `developing` (40–59), `proficient` (60–79), `strong` (80–100).
   - Recency weighting: $N = (P \times 0.70) + (C \times 0.30)$.
