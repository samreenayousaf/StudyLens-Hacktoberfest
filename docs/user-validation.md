# StudyLens — Student User Validation Protocol

**Status:** Validation Pending (Template & Protocol Prepared)  
**Target User:** Classmate / Computer Science Student  

---

## 1. Objective

The objective of this user validation protocol is to test StudyLens with a real student to observe:
1. Whether the local AI analysis correctly extracts concept-level understanding from written student answers.
2. Whether detected misconceptions match the student's actual reasoning.
3. Whether the targeted same-concept retesting behavior feels helpful and relevant for reinforcing weak concepts.

---

## 2. Privacy & Data Handling Protocol

> [!IMPORTANT]
> **Strict Privacy Guidelines:**
> - **No Personal Data Collection:** Do NOT record the participant's name, email, phone number, student ID, or personal academic records.
> - **Local Processing:** All student answer text is processed locally by the FastAPI backend and local Ollama instance (`gemma3:1b`). No data is sent to external cloud APIs.
> - **Anonymized Observation Only:** Record only qualitative feedback and observation notes using the anonymized template below.

---

## 3. Step-by-Step Validation Procedure

1. **Introduction & Consent:**
   - Briefly explain StudyLens: *"StudyLens is a local AI tool that analyzes written answers to Software Engineering questions, estimates concept-level understanding, updates mastery, and suggests retest questions when helpful."*
   - Confirm voluntary participation and inform the student that no personal data will be collected or stored.
2. **Initial Assessment:**
   - Launch StudyLens on `http://localhost:5173`.
   - Ask the student to answer 2–3 questions in their own words without looking up answers.
3. **AI Analysis Review:**
   - Observe the student's reaction to the generated feedback, detected concepts, misconceptions, and estimated score.
   - Ask: *"Does this feedback accurately describe what you understood or missed in your answer?"*
4. **Adaptive Retest Verification:**
   - If a retest is suggested (e.g. for a weak concept or misconception), ask the student to click **Continue Retest** and answer the follow-up question.
   - Observe whether the follow-up question targeted the correct concept.
5. **Debriefing:**
   - Ask qualitative feedback questions about clarity, speed, and helpfulness.

---

## 4. Anonymized Observation Template

```text
======================================================================
                     STUDYLENS USER VALIDATION RECORD
======================================================================
Participant ID:           [e.g., Student-01]
Student Academic Level:   [e.g., Undergraduate CS / Software Engineering]
Subject Familiarity:      [e.g., Intermediate]

Questions Attempted:
  1. Concept: [e.g., Coupling]
     Question: "What is meant by high coupling in software design?"
     Student Response Summary: [...]
     Observed AI Score: [.../100]
     AI Detected Misconceptions: [...]

Observed Useful Behavior:
  - [...]

Observed Incorrect / Misleading Behavior:
  - [...]

Qualitative Questions:
  - Was the retest question relevant to your weak area?
    [ ] Yes   [ ] No   [ ] Partially

  - Did the feedback help identify what was missing in your explanation?
    [ ] Yes   [ ] No   [ ] Partially

User Comments:
  "[...]"

Limitations Noticed During Session:
  - [...]
======================================================================
STATUS: VALIDATION PENDING (Awaiting live classmate trial session)
```
