# StudyLens — 3–5 Minute Hacktoberfest Demo Script

**Total Estimated Duration:** 3 minutes 30 seconds  
**Prerequisites:** Backend running (`http://127.0.0.1:8000`), Ollama active (`gemma3:1b`), Frontend open (`http://localhost:5173`).  

---

## 0:00 – 0:30 | Introduction & Concept Overview

* **Screen:** StudyLens Dashboard (`/`).
* **Speaker Script:**
  > *"Hi everyone! Welcome to StudyLens — a private, local-AI assessment tool for Software Engineering students. Unlike traditional multiple-choice quizzes, StudyLens allows students to write full explanations in their own words. It uses a locally running Gemma 3:1B model to analyze answers and extract misconceptions, while a deterministic Python engine updates concept mastery and targets retest practice — completely offline with zero cloud API dependencies."*

---

## 0:30 – 1:15 | Dashboard & Initial Question

* **Screen:** Dashboard showing concept list (`Coupling`, `Cohesion`, `Requirements Engineering`, etc.) with initial unassessed state.
* **Action:** Click **"Start Assessment"** to navigate to `/assessment`.
* **Speaker Script:**
  > *"Here on the dashboard, we see 11 core Software Engineering concepts. Clicking 'Start Assessment' loads our first question from the backend."*
* **Question Displayed:**
  > *"What is meant by high coupling in software design?"*

---

## 1:15 – 2:00 | Case 1: Strong Answer Demonstration

* **Action:** Enter strong answer:
  > *"High coupling means modules depend strongly on each other. This is usually undesirable because changing one module can affect other modules."*
* **Action:** Click **"Submit Answer"**. Observe loading spinner while local Gemma 3:1B processes the answer.
* **Result Displayed:**
  > - Understanding Score: `65–75 / 100` (Proficient)
  > - Detected Concept: `Coupling`
  > - Feedback / Evidence text explaining correct identification of module dependency.
  > - Mastery badge updated to **Proficient**.
  > - Retest Decision: **No immediate retest required.**
* **Speaker Script:**
  > *"Notice how Gemma analyzed our answer locally and returned structured evidence. Because the score meets proficiency and no major misconception was detected, the deterministic mastery engine updates our Coupling mastery score without requiring an immediate retest."*

---

## 2:00 – 3:00 | Case 2: Misconception & Adaptive Retest Trigger

* **Action:** Navigate back to Assessment or click Next Question.
* **Question Displayed:**
  > *"Which situation represents high coupling between two software modules, and why is it usually undesirable?"*
* **Action:** Enter misconception answer:
  > *"High coupling is good because all code is in one giant file and modules share everything."*
* **Action:** Click **"Submit Answer"**.
* **Result Displayed:**
  > - Understanding Score: `40 / 100` (Developing / Weak)
  > - Detected Misconception: *"High coupling is good / single giant file preference"*
  > - Mastery updated downwards to **Developing**.
  > - Retest Triggered: **"Targeted Retest Suggested for Coupling"**
  > - Active Button: **"Continue Retest"**
* **Speaker Script:**
  > *"This time, the student submitted a clear misconception — claiming high coupling in a single file is good. Gemma extracted this specific misconception, and our deterministic mastery engine flagged Coupling for an immediate retest."*

---

## 3:00 – 3:30 | Explicit Retest Continuation & Conclusion

* **Action:** Click **"Continue Retest"**.
* **Targeted Question Displayed:**
  > *"How can a software developer reduce coupling between modules?"* (Another active, unanswered question belonging to the same `Coupling` concept).
* **Speaker Script:**
  > *"Clicking 'Continue Retest' explicitly fetches another active question targeting the exact same concept. Notice that StudyLens never automatically submits retest questions without explicit student action."*
* **Closing Statement:**
  > *"In summary, StudyLens combines the interpretative power of local open-weight models like Gemma 3:1B with the safety and predictability of deterministic Python mastery algorithms. Thank you for watching!"*
