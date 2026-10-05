import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
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


def test_exactly_11_active_concepts():
    """Verify there are exactly 11 active concepts in the database."""
    db = SessionLocal()
    try:
        active_concepts = db.query(Concept).filter(Concept.is_active.is_(True)).all()
        assert len(active_concepts) == 11

        concept_names = [c.name for c in active_concepts]
        expected_names = [
            "Requirements Engineering",
            "Functional vs Non-functional Requirements",
            "Agile",
            "Scrum",
            "Waterfall",
            "Coupling",
            "Cohesion",
            "Software Testing",
            "Unit Testing",
            "Integration Testing",
            "Version Control",
        ]
        assert sorted(concept_names) == sorted(expected_names)
    finally:
        db.close()


def test_coupling_exists_once_with_exact_five_active_questions():
    """Verify Coupling exists exactly once and has exactly 5 active questions matching required wording."""
    db = SessionLocal()
    try:
        coupling_matches = db.query(Concept).filter(Concept.name == "Coupling").all()
        assert len(coupling_matches) == 1
        coupling = coupling_matches[0]

        coupling_questions = (
            db.query(Question)
            .filter(
                Question.concept_id == coupling.id,
                Question.is_active.is_(True),
            )
            .all()
        )
        assert len(coupling_questions) == 5

        exact_expected_texts = [
            "What is meant by high coupling in software design?",
            "Which situation represents high coupling between two software modules, and why is it usually undesirable?",
            "How can a software developer reduce coupling between modules?",
            "What is the difference between high coupling and low coupling in software design?",
            "Why does low coupling generally make software easier to maintain, test, and modify?",
        ]

        question_texts = [q.question_text for q in coupling_questions]
        for expected in exact_expected_texts:
            assert expected in question_texts
    finally:
        db.close()


def test_every_concept_has_at_least_one_active_question():
    """Verify every one of the 11 concepts has at least 1 active question."""
    db = SessionLocal()
    try:
        concepts = db.query(Concept).filter(Concept.is_active.is_(True)).all()
        for concept in concepts:
            q_count = (
                db.query(Question)
                .filter(
                    Question.concept_id == concept.id,
                    Question.is_active.is_(True),
                )
                .count()
            )
            assert q_count >= 1, f"Concept '{concept.name}' has no active questions"
    finally:
        db.close()


def test_seed_idempotency_preserves_attempts_and_mastery():
    """Verify running seed_database a second time does not duplicate concepts/questions and preserves attempts/mastery."""
    db = SessionLocal()
    try:
        # Create a sample attempt and mastery record
        concept = db.query(Concept).first()
        question = db.query(Question).filter(Question.concept_id == concept.id).first()

        attempt = Attempt(
            question_id=question.id,
            concept_id=concept.id,
            answer_text="Sample student answer",
            understanding_score=75.0,
            correct=True,
        )
        mastery = Mastery(
            concept_id=concept.id,
            mastery_score=75.0,
            mastery_level="proficient",
            attempts_count=1,
            correct_count=1,
        )
        db.add(attempt)
        db.add(mastery)
        db.commit()

        initial_concept_count = db.query(Concept).count()
        initial_question_count = db.query(Question).count()
        initial_attempt_count = db.query(Attempt).count()
        initial_mastery_count = db.query(Mastery).count()

        # Run seed database a second time
        seed_database(db)

        assert db.query(Concept).count() == initial_concept_count
        assert db.query(Question).count() == initial_question_count
        assert db.query(Attempt).count() == initial_attempt_count
        assert db.query(Mastery).count() == initial_mastery_count

        # Check Coupling still has exactly 5 active questions
        coupling = db.query(Concept).filter(Concept.name == "Coupling").first()
        coupling_q_count = (
            db.query(Question)
            .filter(
                Question.concept_id == coupling.id,
                Question.is_active.is_(True),
            )
            .count()
        )
        assert coupling_q_count == 5
    finally:
        db.close()


def test_get_concepts_endpoint():
    """Verify GET /api/concepts returns 11 active concepts."""
    with TestClient(app) as client:
        response = client.get("/api/concepts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 11
        assert any(c["name"] == "Coupling" for c in data)


def test_get_questions_endpoint():
    """Verify GET /api/questions returns active questions."""
    with TestClient(app) as client:
        response = client.get("/api/questions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 15

        # Test filtering by concept_id
        db = SessionLocal()
        try:
            coupling = db.query(Concept).filter(Concept.name == "Coupling").first()
            coupling_id = coupling.id
        finally:
            db.close()

        res_filtered = client.get(f"/api/questions?concept_id={coupling_id}")
        assert res_filtered.status_code == 200
        filtered_data = res_filtered.json()
        assert len(filtered_data) == 5


def test_get_initial_question_endpoint():
    """Verify GET /api/questions/initial returns question from unassessed concept with required fields."""
    with TestClient(app) as client:
        response = client.get("/api/questions/initial")
        assert response.status_code == 200
        data = response.json()

        # Check required fields for frontend integration
        assert "id" in data
        assert "question_id" in data
        assert "question_text" in data
        assert "concept_id" in data
        assert "concept" in data
        assert data["concept"]["id"] == data["concept_id"]

        # Add an attempt for the returned question's concept and verify next call avoids assessed concepts
        db = SessionLocal()
        try:
            first_concept_id = data["concept_id"]
            question_id = data["id"]
            attempt = Attempt(
                question_id=question_id,
                concept_id=first_concept_id,
                answer_text="Test answer",
                understanding_score=85.0,
                correct=True,
            )
            db.add(attempt)
            db.commit()
        finally:
            db.close()

        response2 = client.get("/api/questions/initial")
        assert response2.status_code == 200
        data2 = response2.json()

        # Must avoid the concept that now has attempts
        assert data2["concept_id"] != first_concept_id
