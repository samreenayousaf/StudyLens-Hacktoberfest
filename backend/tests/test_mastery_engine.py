import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.mastery_service import calculate_mastery, get_mastery_level
from app.models import Attempt, Concept, Mastery, Question
from app.seed import seed_database


@pytest.fixture(scope="function", autouse=True)
def setup_and_seed_db():
    """Reset and seed the database for each test function."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


def test_mastery_level_boundaries():
    """Verify exact mastery level boundaries:
    0–39 -> weak
    40–59 -> developing
    60–79 -> proficient
    80–100 -> strong
    """
    assert get_mastery_level(0) == "weak"
    assert get_mastery_level(39) == "weak"
    assert get_mastery_level(39.9) == "weak"
    assert get_mastery_level(40) == "developing"
    assert get_mastery_level(59) == "developing"
    assert get_mastery_level(59.9) == "developing"
    assert get_mastery_level(60) == "proficient"
    assert get_mastery_level(79) == "proficient"
    assert get_mastery_level(79.9) == "proficient"
    assert get_mastery_level(80) == "strong"
    assert get_mastery_level(100) == "strong"


def test_first_and_subsequent_mastery_calculation():
    """Verify first assessment equals current score and subsequent assessment uses 70/30 formula."""
    # First assessment: None -> 85.0
    first_score = calculate_mastery(None, 85.0)
    assert first_score == 85.0

    # Subsequent assessment: prev=80.0, curr=50.0 -> (80*0.7) + (50*0.3) = 56 + 15 = 71.0
    subsequent_score = calculate_mastery(80.0, 50.0)
    assert pytest.approx(subsequent_score, 0.01) == 71.0


def test_score_clamping():
    """Verify mastery scores below 0 or above 100 are clamped."""
    assert calculate_mastery(None, -15.0) == 0.0
    assert calculate_mastery(None, 120.0) == 100.0
    assert calculate_mastery(100.0, 150.0) == 100.0
    assert calculate_mastery(0.0, -50.0) == 0.0
    assert get_mastery_level(-10) == "weak"
    assert get_mastery_level(150) == "strong"


def test_post_attempt_endpoint_creates_attempt_and_updates_mastery():
    """Verify POST /api/attempts creates Attempt record and updates Mastery."""
    with TestClient(app) as client:
        payload = {
            "question_id": 1,
            "answer_text": "High coupling means components are tightly coupled to each other.",
            "understanding_score": 85.0,
        }
        res = client.post("/api/attempts", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert "attempt" in data
        assert "mastery" in data

        attempt = data["attempt"]
        mastery = data["mastery"]

        assert attempt["question_id"] == 1
        assert attempt["understanding_score"] == 85.0
        assert attempt["correct"] is True

        assert mastery["mastery_score"] == 85.0
        assert mastery["mastery_level"] == "strong"
        assert mastery["attempts_count"] == 1
        assert mastery["correct_count"] == 1


def test_multiple_attempts_update_same_mastery_record_and_correct_count():
    """Verify multiple attempts for questions under the same concept update the single Mastery row."""
    with TestClient(app) as client:
        # First attempt (correct >= 60)
        res1 = client.post(
            "/api/attempts",
            json={
                "question_id": 1,
                "answer_text": "Answer 1",
                "understanding_score": 80.0,
            },
        )
        assert res1.status_code == 201
        m1 = res1.json()["mastery"]
        assert m1["mastery_score"] == 80.0
        assert m1["attempts_count"] == 1
        assert m1["correct_count"] == 1
        assert m1["mastery_level"] == "strong"

        # Second attempt (incorrect < 60)
        # Expected new mastery = (80.0 * 0.70) + (30.0 * 0.30) = 56.0 + 9.0 = 65.0
        res2 = client.post(
            "/api/attempts",
            json={
                "question_id": 2,
                "answer_text": "Answer 2",
                "understanding_score": 30.0,
            },
        )
        assert res2.status_code == 201
        m2 = res2.json()["mastery"]
        assert pytest.approx(m2["mastery_score"], 0.01) == 65.0
        assert m2["attempts_count"] == 2
        assert m2["correct_count"] == 1  # 30.0 < 60, so correct_count remains 1
        assert m2["mastery_level"] == "proficient"

        # Verify only 1 Mastery row exists in DB for this concept
        db = SessionLocal()
        try:
            concept_id = m2["concept_id"]
            mastery_rows = db.query(Mastery).filter(Mastery.concept_id == concept_id).all()
            assert len(mastery_rows) == 1
        finally:
            db.close()


def test_unassessed_concepts_not_returned_in_mastery_or_weak():
    """Verify unassessed concepts are never returned by GET /api/mastery or GET /api/mastery/weak."""
    with TestClient(app) as client:
        # Initially, no attempts have been submitted
        res_all = client.get("/api/mastery")
        assert res_all.status_code == 200
        assert res_all.json() == []

        res_weak = client.get("/api/mastery/weak")
        assert res_weak.status_code == 200
        assert res_weak.json() == []

        # Submit a low score attempt (< 40) for question 1
        client.post(
            "/api/attempts",
            json={
                "question_id": 1,
                "answer_text": "Incorrect answer",
                "understanding_score": 25.0,
            },
        )

        # Now GET /api/mastery returns 1 record
        res_all_after = client.get("/api/mastery")
        assert res_all_after.status_code == 200
        assert len(res_all_after.json()) == 1

        # GET /api/mastery/weak returns 1 weak record
        res_weak_after = client.get("/api/mastery/weak")
        assert res_weak_after.status_code == 200
        weak_list = res_weak_after.json()
        assert len(weak_list) == 1
        assert weak_list[0]["mastery_level"] == "weak"
        assert weak_list[0]["mastery_score"] == 25.0
