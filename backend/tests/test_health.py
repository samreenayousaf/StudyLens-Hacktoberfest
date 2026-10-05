import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Concept, Question, Attempt, Mastery
from app.seed import seed_database


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database tables are created and seeded before tests run."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


def test_health_endpoint():
    """Verify GET /api/health returns HTTP 200 and exact JSON payload."""
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "StudyLens API"
        }


def test_tables_created_and_seeded():
    """Verify database tables are created and seed records exist."""
    db = SessionLocal()
    try:
        concepts_count = db.query(Concept).count()
        assert concepts_count == 11, f"Expected 11 concepts, found {concepts_count}"

        questions_count = db.query(Question).count()
        assert questions_count >= 15, f"Expected at least 15 questions, found {questions_count}"
    finally:
        db.close()
