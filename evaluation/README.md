# StudyLens Evaluation Methodology & Dataset Guide

This module provides a reproducible evaluation harness for StudyLens answer analysis and adaptive learning loop behavior.

## Overview

StudyLens separates local AI interpretation from deterministic mastery logic:
- **Local AI (Gemma 3:1B via Ollama)**: Interprets free-text answers, scores conceptual understanding (0–100), extracts detected concepts, and identifies misconceptions.
- **Deterministic Engine**: Calculates mastery scores (70/30 recency formula), maps mastery levels (`weak`, `developing`, `proficient`, `strong`), and enforces retest policies.

## Dataset Structure (`test_cases.json`)

The dataset consists of controlled Software Engineering evaluation cases covering five core qualitative categories:
1. `strong`: Correct, thorough explanation of the target concept.
2. `misconception`: Explicit incorrect claims (e.g., claiming high coupling is desirable).
3. `acceptable`: Partially complete explanation.
4. `off_topic`: Completely unrelated text.
5. `weak`: Minimal/non-informative answer ("I don't know").

## Running the Evaluation

1. Ensure local backend server is running on `http://127.0.0.1:8000`:
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Execute the evaluation script:
   ```bash
   python evaluation/run_evaluation.py
   ```

## Technical Checks Performed
- **Response Schema Validation**: Valid JSON output containing numeric `understanding_score`, string `evidence`, array `detected_concepts`, and array `misconceptions`.
- **Coupling False-Positive Protection**: Ensures answers supporting low coupling or explaining high coupling as undesirable are NOT misclassified with a "high coupling preference" misconception.
- **Latency Measurement**: Measures per-request local AI inference latency.
