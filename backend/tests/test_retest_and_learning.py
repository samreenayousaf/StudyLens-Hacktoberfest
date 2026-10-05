from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from app.ai.analyzer import AnswerAnalyzer
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Attempt, Concept, Mastery, Question
from app.retest_service import get_next_retest, select_retest_question, should_retest
from app.seed import seed_database


@pytest.fixture(scope="function", autouse=True)
def setup_and_seed_db():
    """Reset and seed the isolated test database for each test function."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


def test_should_retest_decision_rules():
    """Verify exact retest rules:
    - Score < 60: ALWAYS retest.
    - Misconception present: ALWAYS retest.
    - Score >= 60 with no misconceptions: no immediate retest.
    """
    # 1. Weak score (< 60) -> True
    req1, _ = should_retest("proficient", [], understanding_score=45.0)
    assert req1 is True

    # 2. Misconception present -> True
    req2, _ = should_retest("proficient", ["confuses high and low coupling"], understanding_score=75.0)
    assert req2 is True

    # 3. Proficient score + no misconception -> False
    req3, _ = should_retest("proficient", [], understanding_score=85.0)
    assert req3 is False

    # 4. Strong score + no misconception -> False
    req4, _ = should_retest("strong", [], understanding_score=90.0)
    assert req4 is False


def test_case1_strong_current_answer():
    """Case 1: Current score = 85, Misconceptions = [] -> no immediate retest."""
    req, _ = should_retest("proficient", misconceptions=[], understanding_score=85.0)
    assert req is False


def test_case2_weak_current_answer():
    """Case 2: Current score = 45, Misconceptions = [] -> retest required."""
    req, _ = should_retest("proficient", misconceptions=[], understanding_score=45.0)
    assert req is True


def test_case3_good_score_but_meaningful_misconception():
    """Case 3: Current score = 75, Misconceptions = ["incorrect claim"] -> retest required."""
    req, _ = should_retest("proficient", misconceptions=["incorrect claim"], understanding_score=75.0)
    assert req is True


def test_case4_strong_answer_with_no_misconceptions():
    """Case 4: Current score = 90, Misconceptions = [] -> no retest."""
    req, _ = should_retest("strong", misconceptions=[], understanding_score=90.0)
    assert req is False


@patch.object(AnswerAnalyzer, "analyze")
def test_case5_previous_mastery_high_current_answer_weak(mock_analyze):
    """Case 5: Previous mastery = 85, Current score = 45, Misconceptions = ["incorrect claim"]
    -> Mastery remains 73% (Proficient), BUT retest_required must be True.
    """
    db = SessionLocal()
    try:
        scrum = db.query(Concept).filter(Concept.name == "Scrum").first()
        scrum_q1 = db.query(Question).filter(Question.concept_id == scrum.id).first()

        # Set previous mastery to 85.0 (Strong)
        mastery = Mastery(
            concept_id=scrum.id,
            mastery_score=85.0,
            mastery_level="strong",
            attempts_count=1,
            correct_count=1,
        )
        db.add(mastery)
        db.commit()

        # Mock AI returning score 45.0 with misconception
        mock_analyze.return_value = {
            "understanding_score": 45.0,
            "detected_concepts": ["Scrum"],
            "misconceptions": ["The roles are interchangeable"],
            "evidence": "Weak explanation of Scrum roles.",
        }

        with TestClient(app) as client:
            payload = {
                "question_id": scrum_q1.id,
                "answer_text": "Scrum roles are interchangeable.",
            }
            res = client.post("/api/learning/submit-answer", json=payload)
            assert res.status_code == 200
            data = res.json()

            # Formula check: (85 * 0.70) + (45 * 0.30) = 59.5 + 13.5 = 73.0%
            assert data["mastery"]["mastery_score"] == 73.0
            assert data["mastery"]["mastery_level"] == "proficient"

            # Retest MUST be required despite 73% Proficient mastery
            assert data["retest"]["required"] is True
            assert data["retest"]["concept"] == "Scrum"
            assert data["retest"]["concept_id"] == scrum.id
    finally:
        db.close()


def test_case6_same_concept_targeting_scrum():
    """Case 6: If Scrum triggers a retest, next question MUST belong to Scrum and never another concept."""
    db = SessionLocal()
    try:
        scrum = db.query(Concept).filter(Concept.name == "Scrum").first()

        retest_q = select_retest_question(db, scrum.id)
        assert retest_q is not None
        assert retest_q.concept_id == scrum.id

        scrum_concept = db.query(Concept).filter(Concept.id == retest_q.concept_id).first()
        assert scrum_concept.name == "Scrum"
        assert scrum_concept.name not in ["Agile", "Coupling", "Waterfall"]
    finally:
        db.close()


def test_same_concept_targeting():
    """Verify retest targeting strictly selects questions from the same concept."""
    db = SessionLocal()
    try:
        coupling = db.query(Concept).filter(Concept.name == "Coupling").first()
        req_eng = db.query(Concept).filter(Concept.name == "Requirements Engineering").first()

        # Target Coupling
        q_coupling = select_retest_question(db, coupling.id)
        assert q_coupling is not None
        assert q_coupling.concept_id == coupling.id

        # Target Requirements Engineering
        q_req = select_retest_question(db, req_eng.id)
        assert q_req is not None
        assert q_req.concept_id == req_eng.id
    finally:
        db.close()


def test_question_selection_preference_and_fallback():
    """Verify question selection prefers unanswered questions, handles multiple unanswered deterministically,
    falls back when all are attempted, and excludes inactive questions.
    """
    db = SessionLocal()
    try:
        coupling = db.query(Concept).filter(Concept.name == "Coupling").first()

        # Initially all 5 Coupling questions are unanswered. First choice is Q1 (lowest ID)
        q1 = select_retest_question(db, coupling.id)
        assert q1.id == 1

        # Attempt Q1
        db.add(Attempt(question_id=1, concept_id=coupling.id, answer_text="Ans", understanding_score=30.0, correct=False))
        db.commit()

        # Next preferred unanswered question is Q2 (id 2)
        q2 = select_retest_question(db, coupling.id)
        assert q2.id == 2

        # Mark an active question as inactive and verify it is never selected
        q3 = db.query(Question).filter(Question.id == 3).first()
        q3.is_active = False
        db.commit()

        # Attempt remaining active Coupling questions (Q2, Q4, Q5)
        for q_id in [2, 4, 5]:
            db.add(Attempt(question_id=q_id, concept_id=coupling.id, answer_text="Ans", understanding_score=30.0, correct=False))
        db.commit()

        # Now all active Coupling questions (1, 2, 4, 5) have been attempted
        fallback_q = select_retest_question(db, coupling.id)
        assert fallback_q is not None
        assert fallback_q.is_active is True
        assert fallback_q.concept_id == coupling.id
        assert fallback_q.id != 3  # Inactive question 3 is never selected
    finally:
        db.close()


@patch.object(AnswerAnalyzer, "analyze")
def test_post_learning_submit_answer_full_flow(mock_analyze):
    """Verify POST /api/learning/submit-answer creates 1 Attempt, updates Mastery, returns AI analysis & retest payload."""
    mock_analyze.return_value = {
        "understanding_score": 35.0,
        "detected_concepts": ["Coupling"],
        "misconceptions": ["high coupling preference"],
        "evidence": "Student prefers high coupling.",
    }

    with TestClient(app) as client:
        payload = {
            "question_id": 1,
            "answer_text": "I prefer high coupling between modules.",
        }
        res = client.post("/api/learning/submit-answer", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert "analysis" in data
        assert "attempt" in data
        assert "mastery" in data
        assert "retest" in data

        # AI analysis checks
        assert data["analysis"]["understanding_score"] == 35.0
        assert data["analysis"]["detected_concepts"] == ["Coupling"]

        # Attempt checks
        assert data["attempt"]["question_id"] == 1
        assert data["attempt"]["correct"] is False

        # Mastery checks (weak level)
        assert data["mastery"]["mastery_score"] == 35.0
        assert data["mastery"]["mastery_level"] == "weak"
        assert data["mastery"]["attempts_count"] == 1

        # Retest checks
        assert data["retest"]["required"] is True
        assert data["retest"]["concept_id"] == 6
        assert data["retest"]["concept"] == "Coupling"
        assert data["retest"]["question_id"] is not None
        assert data["retest"]["question_id"] != 1  # Prefers unattempted Q2 for retest

        # Verify retest question was NOT automatically attempted
        db = SessionLocal()
        try:
            attempt_count = db.query(Attempt).count()
            assert attempt_count == 1
        finally:
            db.close()


@patch.object(AnswerAnalyzer, "analyze")
def test_rapid_duplicate_submission_protection(mock_analyze):
    """Verify rapid duplicate submission within 5 seconds creates only 1 Attempt."""
    mock_analyze.return_value = {
        "understanding_score": 85.0,
        "detected_concepts": ["Coupling"],
        "misconceptions": [],
        "evidence": "Good answer.",
    }

    with TestClient(app) as client:
        payload = {
            "question_id": 1,
            "answer_text": "Low coupling is desirable.",
        }

        # First submission
        res1 = client.post("/api/learning/submit-answer", json=payload)
        assert res1.status_code == 200

        # Rapid duplicate submission
        res2 = client.post("/api/learning/submit-answer", json=payload)
        assert res2.status_code == 200

        # Verify only 1 Attempt exists in DB
        db = SessionLocal()
        try:
            attempts = db.query(Attempt).filter(Attempt.question_id == 1).all()
            assert len(attempts) == 1
        finally:
            db.close()


def test_get_retest_next_endpoint():
    """Verify GET /api/retest/next returns required=False when unassessed/strong, and required=True when weak."""
    with TestClient(app) as client:
        # Initially unassessed
        res1 = client.get("/api/retest/next")
        assert res1.status_code == 200
        assert res1.json()["required"] is False

        # Submit a low score attempt directly via Mastery/Attempt
        db = SessionLocal()
        try:
            coupling = db.query(Concept).filter(Concept.name == "Coupling").first()
            mastery = Mastery(
                concept_id=coupling.id,
                mastery_score=30.0,
                mastery_level="weak",
                attempts_count=1,
                correct_count=0,
            )
            attempt = Attempt(
                question_id=1,
                concept_id=coupling.id,
                answer_text="Weak ans",
                understanding_score=30.0,
                correct=False,
            )
            db.add(mastery)
            db.add(attempt)
            db.commit()
        finally:
            db.close()

        res2 = client.get("/api/retest/next")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["required"] is True
        assert data2["concept_id"] == 6
        assert data2["concept"] == "Coupling"
        assert data2["question_id"] == 2  # Unanswered question Q2
