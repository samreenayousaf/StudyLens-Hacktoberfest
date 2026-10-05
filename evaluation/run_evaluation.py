#!/usr/bin/env python3
"""StudyLens Evaluation Script.

Evaluates local AI answer analysis and adaptive learning loop behavior
against controlled Software Engineering test cases.
"""

import json
import os
import sys
import time
import requests

BACKEND_URL = os.getenv("STUDYLENS_API_URL", "http://127.0.0.1:8000")
TEST_CASES_PATH = os.path.join(os.path.dirname(__file__), "test_cases.json")


def check_backend_health():
    """Verify local FastAPI backend and health status."""
    try:
        res = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        if res.status_code == 200 and res.json().get("status") == "ok":
            return True
    except Exception:
        pass
    return False


def run_evaluations():
    """Run evaluation suite against active backend."""
    print("=" * 70)
    print("      STUDYLENS LOCAL AI & ADAPTIVE ENGINE EVALUATION SUITE")
    print("=" * 70)

    if not check_backend_health():
        print(f"[ERROR] Cannot connect to StudyLens backend at {BACKEND_URL}.")
        print("Please start the backend server first:")
        print("  cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)

    print(f"[OK] Connected to backend at {BACKEND_URL}.")

    if not os.path.exists(TEST_CASES_PATH):
        print(f"[ERROR] Test cases file not found at {TEST_CASES_PATH}.")
        sys.exit(1)

    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"[INFO] Loaded {len(cases)} evaluation test cases.\n")

    results = []
    total_latency = 0.0

    for idx, case in enumerate(cases, 1):
        print(f"[{idx}/{len(cases)}] Case '{case['id']}' ({case['category']}) - Concept: {case['concept_name']}")
        print(f"  Question: \"{case['question_text']}\"")
        print(f"  Answer:   \"{case['answer_text']}\"")

        start_time = time.time()
        try:
            res = requests.post(
                f"{BACKEND_URL}/api/ai/analyze-answer",
                json={
                    "question_id": case["question_id"],
                    "answer_text": case["answer_text"],
                },
                timeout=120,
            )
            elapsed = time.time() - start_time
            total_latency += elapsed

            if res.status_code != 200:
                print(f"  [FAIL] HTTP status {res.status_code}: {res.text}\n")
                results.append({"case": case, "success": False, "error": res.text})
                continue

            data = res.json()
            score = data.get("understanding_score", 0.0)
            concepts = data.get("detected_concepts", [])
            misconceptions = data.get("misconceptions", [])
            evidence = data.get("evidence", "")

            # Schema validation
            valid_schema = (
                isinstance(score, (int, float))
                and 0.0 <= score <= 100.0
                and isinstance(concepts, list)
                and isinstance(misconceptions, list)
                and isinstance(evidence, str)
                and len(evidence) > 0
            )

            # Coupling False Positive check
            is_coupling_protected = True
            if case["concept_name"] == "Coupling" and case["category"] == "strong":
                if any("high coupling preference" in m.lower() for m in misconceptions):
                    is_coupling_protected = False

            print(f"  Latency: {elapsed:.2f}s | Score: {score:.1f}/100 | Schema Valid: {valid_schema}")
            print(f"  Detected Concepts: {concepts}")
            print(f"  Misconceptions:    {misconceptions}")
            print(f"  Evidence Summary:  \"{evidence[:80]}...\"")

            if not is_coupling_protected:
                print("  [WARN] Coupling false-positive protection failed!")

            print("-" * 70)

            results.append({
                "case": case,
                "success": valid_schema and is_coupling_protected,
                "latency": elapsed,
                "score": score,
                "concepts": concepts,
                "misconceptions": misconceptions,
                "evidence": evidence,
            })

        except Exception as exc:
            elapsed = time.time() - start_time
            print(f"  [ERROR] Execution failed: {exc}\n")
            results.append({"case": case, "success": False, "error": str(exc)})

    # Summary Statistics
    successful_runs = [r for r in results if r.get("success")]
    avg_latency = total_latency / len(cases) if cases else 0.0

    print("\n" + "=" * 70)
    print("                     EVALUATION SUMMARY REPORT")
    print("=" * 70)
    print(f"Total Test Cases:       {len(cases)}")
    print(f"Successful & Valid:     {len(successful_runs)} / {len(cases)}")
    print(f"Average AI Latency:     {avg_latency:.2f} seconds / request")
    print("=" * 70)

    if len(successful_runs) == len(cases):
        print("RESULT: ALL EVALUATION TEST CASES PASSED SCHEMA & SAFETY CHECKS.")
    else:
        print("RESULT: SOME TEST CASES FAILED OR RETURNED INVALID SCHEMA.")


if __name__ == "__main__":
    run_evaluations()
