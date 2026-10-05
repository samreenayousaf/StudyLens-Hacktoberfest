# StudyLens — Hacktoberfest 2026 Project Pitch

**Project Name:** StudyLens  
**Category:** Open-Source AI & Open-Weight Models  
**Primary Model:** Gemma 3:1B (via Ollama)  
**Target Event:** Hacktoberfest 2026 DEV Challenge (*"AI belongs to everyone"*)  

---

## 1. Problem Statement

Conventional automated assessment systems in computer science education rely almost exclusively on multiple-choice quizzes or binary pass/fail unit tests. While multiple-choice questions are easy to score deterministically, they fail to evaluate a student's conceptual reasoning, written explanations, or underlying mental models. Conversely, when students write free-form explanations, conventional platforms cannot detect specific misconceptions or offer targeted follow-up practice without manual teacher grading.

---

## 2. Existing Limitations of Generic AI Chatbots

Generic conversational AI interfaces (e.g. standard ChatGPT or generic chat widgets) are frequently used by students, but present major architectural drawbacks for structured learning:
- **Lack of Persistent Mastery State:** Chatbots converse in unstructured text without maintaining a deterministic, reproducible model of concept-level mastery.
- **Hallucinated Grading:** Allowing an LLM to directly assign final grades or control progression leads to non-deterministic, fluctuating scores for identical answers.
- **Privacy Concerns:** Sending student written answers to external cloud AI endpoints exposes educational data to third-party providers.

---

## 3. The StudyLens Solution

StudyLens solves these limitations through a **private, local-AI adaptive assessment system** built specifically for Software Engineering concepts.

```text
Student Written Answer
          │
          ▼
Local Gemma 3:1B (Ollama)   ──► Interprets explanation & extracts evidence
          │
          ▼
Deterministic Python Engine  ──► Updates concept mastery & checks retest rules
          │
          ▼
Targeted Same-Concept Retest ──► Selects unanswered question for reinforcement
```

---

## 4. Key Technical Innovation: Separation of Concerns

A core technical design decision in StudyLens is the strict separation between the **AI Interpretation Layer** and the **Deterministic Learning Engine**:

1. **Local LLM as Interpreter Only:**
   - The local Gemma 3:1B model analyzes written responses to extract structured qualitative evidence: an estimated understanding score ($0–100$), detected concepts, specific misconceptions, and textual evidence.
   - The LLM does **NOT** store state, calculate final mastery levels, or decide retest rules.

2. **Deterministic Python Engine as Authority:**
   - A pure Python backend service (`mastery_service.py`) calculates concept mastery using an explicit recency-weighted formula ($0.70 \times \text{previous} + 0.30 \times \text{current}$).
   - Mastery levels (`weak`, `developing`, `proficient`, `strong`) and retest decisions are computed deterministically.
   - Retest questions are selected by `retest_service.py` targeting the exact weak concept without LLM hallucination.

---

## 5. Why Local Open-Weight AI?

* **Privacy by Design:** Student written answers never leave the local machine. Core AI analysis runs entirely offline via Ollama.
* **Zero API Costs:** No reliance on paid cloud LLM APIs or external tokens.
* **Reproducibility:** Developers and educators can clone the repository, pull `gemma3:1b`, and run the exact same evaluation suite locally.

---

## 6. Practical Student Benefit & Current Limitations

* **Practical Benefit:** Students receive instant feedback on their written explanations, clear identification of specific misconceptions, and immediate targeted follow-up practice on concepts that need improvement.
* **Current Limitations:**
  - Gemma 3:1B is a small local model; complex edge-case explanations may occasionally require model output sanitization.
  - Seeding is currently focused on 11 core Software Engineering concepts.
  - Inference speed depends on local CPU/GPU hardware.
