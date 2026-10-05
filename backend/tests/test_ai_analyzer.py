from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status
from app.ai.analyzer import AnswerAnalyzer
from app.ai.ollama_client import OllamaClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Attempt, Mastery, Question
from app.seed import seed_database


@pytest.fixture(scope="function", autouse=True)
def setup_and_seed_db():
    """Reset and seed database for each test function."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


def test_valid_structured_ai_response():
    """Verify analyzer correctly parses valid JSON AI responses."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = '''{
        "understanding_score": 85.0,
        "detected_concepts": ["Coupling"],
        "misconceptions": [],
        "evidence": "Student accurately explains tight dependencies between software modules."
    }'''

    analyzer = AnswerAnalyzer(ollama_client=mock_client)
    res = analyzer.analyze(
        question_text="What is meant by high coupling in software design?",
        target_concept_name="Coupling",
        target_concept_description="Degree of interdependence",
        student_answer="High coupling means modules depend heavily on each other.",
        known_concepts=["Coupling", "Cohesion", "Agile"],
    )

    assert res["understanding_score"] == 85.0
    assert res["detected_concepts"] == ["Coupling"]
    assert res["misconceptions"] == []
    assert "tight dependencies" in res["evidence"]


def test_score_clamping_and_invalid_score_handling():
    """Verify understanding_score is clamped between 0 and 100."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    # Over 100
    res1 = analyzer.parse_and_normalize_response(
        raw_response='{"understanding_score": 150, "detected_concepts": ["Coupling"]}',
        target_concept_name="Coupling",
        student_answer="Test",
        known_concepts=["Coupling"],
    )
    assert res1["understanding_score"] == 100.0

    # Under 0
    res2 = analyzer.parse_and_normalize_response(
        raw_response='{"understanding_score": -40, "detected_concepts": ["Coupling"]}',
        target_concept_name="Coupling",
        student_answer="Test",
        known_concepts=["Coupling"],
    )
    assert res2["understanding_score"] == 0.0

    # Non-numeric string
    res3 = analyzer.parse_and_normalize_response(
        raw_response='{"understanding_score": "invalid", "detected_concepts": ["Coupling"]}',
        target_concept_name="Coupling",
        student_answer="Test",
        known_concepts=["Coupling"],
    )
    assert res3["understanding_score"] == 50.0


def test_markdown_and_malformed_json_handling():
    """Verify analyzer handles markdown codeblocks and malformed JSON cleanly."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    # Wrapped in markdown ```json ... ```
    markdown_response = """```json
    {
        "understanding_score": 90,
        "detected_concepts": ["Coupling"],
        "misconceptions": [],
        "evidence": "Good answer."
    }
    ```"""
    res1 = analyzer.parse_and_normalize_response(
        raw_response=markdown_response,
        target_concept_name="Coupling",
        student_answer="Test answer",
        known_concepts=["Coupling"],
    )
    assert res1["understanding_score"] == 90.0
    assert res1["evidence"] == "Good answer."

    # Completely malformed raw text
    malformed_response = "I think the student's answer is score 75 out of 100."
    res2 = analyzer.parse_and_normalize_response(
        raw_response=malformed_response,
        target_concept_name="Coupling",
        student_answer="Test answer",
        known_concepts=["Coupling"],
    )
    assert 0.0 <= res2["understanding_score"] <= 100.0
    assert res2["detected_concepts"] == ["Coupling"]


def test_unknown_concept_filtering():
    """Verify detected_concepts is filtered against known active concepts."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    raw_response = '{"understanding_score": 80, "detected_concepts": ["Coupling", "UnknownConcept123", "agile"]}'
    res = analyzer.parse_and_normalize_response(
        raw_response=raw_response,
        target_concept_name="Coupling",
        student_answer="Test answer discussing coupling and agile principles.",
        known_concepts=["Coupling", "Agile", "Scrum"],
    )
    assert "UnknownConcept123" not in res["detected_concepts"]
    assert "Coupling" in res["detected_concepts"]
    assert "Agile" in res["detected_concepts"]


def test_coupling_false_positive_protection():
    """Verify answers supporting low coupling do NOT produce false high-coupling preference misconceptions."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = "Low coupling is preferred because it makes modules easier to maintain and test."
    raw_ai_output = '''{
        "understanding_score": 85,
        "detected_concepts": ["Coupling"],
        "misconceptions": ["high coupling preference"],
        "evidence": "Student discusses low coupling."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Coupling",
        student_answer=student_answer,
        known_concepts=["Coupling"],
    )

    # Spurious misconception should be stripped
    assert "high coupling preference" not in res["misconceptions"]
    assert len(res["misconceptions"]) == 0


def test_1_correct_agile_answer_false_positive_prevention():
    """Test 1: Correct Agile answer must not produce false rigid/Waterfall or solely customer involvement misconceptions."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Agile focuses on collaboration, working software, customer involvement, and adapting to changing requirements. "
        "Instead of strictly following a fixed plan, Agile teams deliver software incrementally and respond to customer and project changes."
    )
    raw_ai_output = '''{
        "understanding_score": 75,
        "detected_concepts": ["Agile"],
        "misconceptions": [
            "Agile is a rigid, sequential methodology like Waterfall.",
            "The Manifesto focuses solely on customer involvement, neglecting technical aspects."
        ],
        "evidence": "Student accurately describes Agile principles."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Agile",
        student_answer=student_answer,
        known_concepts=["Agile", "Scrum", "Waterfall"],
    )

    assert res["understanding_score"] >= 60.0
    assert "Agile" in res["detected_concepts"]
    assert "Agile is a rigid, sequential methodology like Waterfall." not in res["misconceptions"]
    assert "The Manifesto focuses solely on customer involvement, neglecting technical aspects." not in res["misconceptions"]
    assert res["misconceptions"] == []


def test_2_correct_agile_four_values_no_fabricated_misconceptions():
    """Test 2: Correct Agile answer listing all 4 values must not produce fabricated misconceptions about purpose or technical aspects."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Agile values individuals and interactions over processes and tools, working software over comprehensive documentation, "
        "customer collaboration over contract negotiation, and responding to change over following a plan."
    )
    raw_ai_output = '''{
        "understanding_score": 90,
        "detected_concepts": ["Agile"],
        "misconceptions": [
            "The student doesn't explicitly state the purpose of the Agile Manifesto",
            "The student doesn't fully articulate why these values are important",
            "The Manifesto focuses solely on customer involvement"
        ],
        "evidence": "Student correctly states all four Agile Manifesto values."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Agile",
        student_answer=student_answer,
        known_concepts=["Agile"],
    )

    assert res["understanding_score"] == 90.0
    assert res["misconceptions"] == []


def test_3_genuine_wrong_agile_answer():
    """Test 3: Genuine wrong Agile answer must detect real misconceptions and trigger retest."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Agile means following a fixed plan from beginning to end. The main goal is to complete all documentation "
        "before writing software, and customer changes should generally be avoided."
    )
    raw_ai_output = '''{
        "understanding_score": 25,
        "detected_concepts": ["Agile"],
        "misconceptions": [
            "Believes Agile requires following a fixed plan",
            "Believes documentation must be completed before writing software"
        ],
        "evidence": "Student describes Waterfall practices instead of Agile."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Agile",
        student_answer=student_answer,
        known_concepts=["Agile"],
    )

    assert res["understanding_score"] == 25.0
    assert len(res["misconceptions"]) == 2
    assert "Believes Agile requires following a fixed plan" in res["misconceptions"]


def test_4_genuine_wrong_coupling_answer():
    """Test 4: Genuine wrong Coupling answer must detect real misconception and trigger retest."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = "High coupling means modules are mostly independent and have very few dependencies."
    raw_ai_output = '''{
        "understanding_score": 30,
        "detected_concepts": ["Coupling"],
        "misconceptions": ["Reverses definition of high coupling"],
        "evidence": "Student incorrectly claims high coupling means few dependencies."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Coupling",
        student_answer=student_answer,
        known_concepts=["Coupling"],
    )

    assert res["understanding_score"] == 30.0
    assert "Coupling" in res["detected_concepts"]
    assert "Reverses definition of high coupling" in res["misconceptions"]


def test_5_correct_scrum_answer_no_fabricated_misconceptions():
    """Test 5: Correct Scrum answer must not generate fabricated role interchangeability misconceptions."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "The three primary roles in Scrum are Product Owner, Scrum Master, and Developers. "
        "The Product Owner manages the product backlog, the Scrum Master facilitates team processes and removes impediments, "
        "and Developers build usable increments."
    )
    raw_ai_output = '''{
        "understanding_score": 85,
        "detected_concepts": ["Scrum"],
        "misconceptions": [
            "The roles are interchangeable",
            "The Product Owner is solely responsible for the product's value"
        ],
        "evidence": "Student accurately describes all three Scrum roles."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Scrum",
        student_answer=student_answer,
        known_concepts=["Scrum"],
    )

    assert res["understanding_score"] == 85.0
    assert res["misconceptions"] == []


def test_6_genuine_wrong_scrum_answer():
    """Test 6: Genuine wrong Scrum answer must detect genuine role misconceptions and trigger retest."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = "The Product Owner writes all the code, the Scrum Master assigns every task, and Developers decide the business priorities."
    raw_ai_output = '''{
        "understanding_score": 20,
        "detected_concepts": ["Scrum"],
        "misconceptions": [
            "Believes Product Owner writes all the code",
            "Believes Scrum Master assigns every task"
        ],
        "evidence": "Student completely misidentifies Scrum role responsibilities."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Scrum",
        student_answer=student_answer,
        known_concepts=["Scrum"],
    )

    assert res["understanding_score"] == 20.0
    assert len(res["misconceptions"]) == 2
    assert "Believes Product Owner writes all the code" in res["misconceptions"]
    assert "Believes Scrum Master assigns every task" in res["misconceptions"]


@patch.object(OllamaClient, "generate")
def test_post_ai_analyze_endpoint_success(mock_generate):
    """Verify POST /api/ai/analyze-answer returns AI analysis without creating attempts or modifying mastery."""
    mock_generate.return_value = '''{
        "understanding_score": 88.0,
        "detected_concepts": ["Coupling"],
        "misconceptions": [],
        "evidence": "Correctly defines high coupling."
    }'''

    with TestClient(app) as client:
        # Initial attempt and mastery counts
        db = SessionLocal()
        try:
            initial_attempts_count = db.query(Attempt).count()
            initial_mastery_count = db.query(Mastery).count()
        finally:
            db.close()

        res = client.post(
            "/api/ai/analyze-answer",
            json={
                "question_id": 1,
                "answer_text": "High coupling means modules depend heavily on each other.",
            },
        )

        assert res.status_code == 200
        data = res.json()
        assert data["understanding_score"] == 88.0
        assert data["detected_concepts"] == ["Coupling"]

        # Verify NO attempt or mastery was created
        db2 = SessionLocal()
        try:
            assert db2.query(Attempt).count() == initial_attempts_count
            assert db2.query(Mastery).count() == initial_mastery_count
        finally:
            db2.close()


def test_ai_analyze_endpoint_question_not_found():
    """Verify POST /api/ai/analyze-answer returns 404 for invalid question_id."""
    with TestClient(app) as client:
        res = client.post(
            "/api/ai/analyze-answer",
            json={
                "question_id": 999999,
                "answer_text": "Some answer",
            },
        )
        assert res.status_code == 404


@patch.object(OllamaClient, "generate")
def test_ai_analyze_endpoint_ollama_unavailable(mock_generate):
    """Verify HTTP 503 is returned when Ollama service is unavailable."""
    mock_generate.side_effect = HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Local Ollama service is not reachable.",
    )

    with TestClient(app) as client:
        res = client.post(
            "/api/ai/analyze-answer",
            json={
                "question_id": 1,
                "answer_text": "Some answer",
            },
        )
        assert res.status_code == 503
        assert "Ollama" in res.json()["detail"]


def test_a_correct_waterfall_answer():
    """Test A: Correct Waterfall answer must receive high score (>=80), detected_concepts = ['Waterfall'], misconceptions = [], retest_required = false."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Waterfall is most appropriate for projects with stable, well-defined requirements that are unlikely to change significantly. "
        "It works well when requirements can be specified upfront and the development process can proceed through sequential phases such as requirements, design, implementation, testing, and deployment."
    )
    raw_ai_output = '''{
        "understanding_score": 90,
        "detected_concepts": ["Waterfall"],
        "misconceptions": [],
        "evidence": "Student correctly identifies Waterfall applicability to stable requirement projects."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Waterfall",
        student_answer=student_answer,
        known_concepts=["Waterfall", "Requirements Engineering", "Agile", "Scrum"],
    )

    assert res["understanding_score"] >= 80.0
    assert res["detected_concepts"] == ["Waterfall"]
    assert res["misconceptions"] == []


def test_b_wrong_waterfall_answer():
    """Test B: Wrong Waterfall answer must receive low score (<=40), detected_concepts = ['Waterfall'], genuine misconception, retest_required = true."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Waterfall is best for projects where requirements change frequently and customers need continuous involvement. "
        "It is designed to allow teams to modify requirements easily throughout development, with testing and implementation happening continuously alongside development."
    )
    raw_ai_output = '''{
        "understanding_score": 95,
        "detected_concepts": ["Waterfall", "Requirements Engineering", "Functional vs Non-functional Requirements", "Agile", "Scrum", "Coupling", "Software Testing", "Unit Testing", "Integration Testing"],
        "misconceptions": ["Waterfall is suitable for projects with constantly changing requirements."],
        "evidence": "The student correctly describes Waterfall."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Waterfall",
        student_answer=student_answer,
        known_concepts=["Waterfall", "Requirements Engineering", "Functional vs Non-functional Requirements", "Agile", "Scrum", "Coupling", "Software Testing", "Unit Testing", "Integration Testing"],
    )

    assert res["understanding_score"] <= 40.0
    assert res["detected_concepts"] == ["Waterfall"]
    assert len(res["misconceptions"]) >= 1
    assert any("changing requirements" in m.lower() or "frequently" in m.lower() for m in res["misconceptions"])


def test_c_correct_coupling_answer():
    """Test C: Correct Coupling answer must receive high score (>=80), detected_concepts = ['Coupling'], misconceptions = [], retest_required = false."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Low coupling means software modules have few dependencies on each other. "
        "This is generally desirable because changes in one module are less likely to affect other modules, making the system easier to maintain, test, and modify."
    )
    raw_ai_output = '''{
        "understanding_score": 85,
        "detected_concepts": ["Coupling", "Software Testing"],
        "misconceptions": [],
        "evidence": "Student accurately explains low coupling and few module dependencies."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Coupling",
        student_answer=student_answer,
        known_concepts=["Coupling", "Agile", "Scrum", "Software Testing"],
    )

    assert res["understanding_score"] >= 80.0
    assert res["detected_concepts"] == ["Coupling"]
    assert res["misconceptions"] == []


def test_d_wrong_coupling_answer():
    """Test D: Wrong Coupling answer must receive low score (<=40), detected_concepts = ['Coupling'], genuine misconception, retest_required = true."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = "High coupling is desirable because it means modules have very few dependencies, so changing one module will not affect other modules."
    raw_ai_output = '''{
        "understanding_score": 90,
        "detected_concepts": ["Coupling"],
        "misconceptions": ["Reverses definition of high coupling by claiming high coupled modules have very few dependencies."],
        "evidence": "Student reverses the meaning of high coupling."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Coupling",
        student_answer=student_answer,
        known_concepts=["Coupling"],
    )

    assert res["understanding_score"] <= 40.0
    assert res["detected_concepts"] == ["Coupling"]
    assert len(res["misconceptions"]) >= 1


def test_e_correct_agile_regression():
    """Test E: Correct Agile answer regression check."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Agile focuses on collaboration, working software, customer involvement, and adapting to changing requirements. "
        "Instead of strictly following a fixed plan, Agile teams deliver software incrementally and respond to customer and project changes."
    )
    raw_ai_output = '''{
        "understanding_score": 90,
        "detected_concepts": ["Agile"],
        "misconceptions": [],
        "evidence": "Student accurately describes Agile values."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Agile",
        student_answer=student_answer,
        known_concepts=["Agile", "Scrum", "Waterfall"],
    )

    assert res["understanding_score"] >= 80.0
    assert res["detected_concepts"] == ["Agile"]
    assert res["misconceptions"] == []


def test_f_wrong_agile_regression():
    """Test F: Wrong Agile answer regression check."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Agile means following a fixed plan from beginning to end. The main goal is to complete all documentation "
        "before writing software, and customer changes should generally be avoided."
    )
    raw_ai_output = '''{
        "understanding_score": 25,
        "detected_concepts": ["Agile"],
        "misconceptions": [
            "Believes Agile requires following a fixed plan",
            "Believes documentation must be completed before writing software"
        ],
        "evidence": "Student describes Waterfall practices instead of Agile."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Agile",
        student_answer=student_answer,
        known_concepts=["Agile"],
    )

    assert res["understanding_score"] <= 40.0
    assert "Agile" in res["detected_concepts"]
    assert len(res["misconceptions"]) >= 1


def test_g_correct_scrum_regression():
    """Test G: Correct Scrum answer regression check."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "The three primary roles in Scrum are Product Owner, Scrum Master, and Developers. "
        "The Product Owner manages the product backlog, the Scrum Master facilitates team processes and removes impediments, "
        "and Developers build usable increments."
    )
    raw_ai_output = '''{
        "understanding_score": 85,
        "detected_concepts": ["Scrum"],
        "misconceptions": [],
        "evidence": "Student accurately describes all three Scrum roles."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Scrum",
        student_answer=student_answer,
        known_concepts=["Scrum"],
    )

    assert res["understanding_score"] >= 80.0
    assert res["detected_concepts"] == ["Scrum"]
    assert res["misconceptions"] == []


def test_h_wrong_scrum_regression():
    """Test H: Wrong Scrum answer regression check."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = "The Product Owner writes all the code, the Scrum Master assigns every task, and Developers decide the business priorities."
    raw_ai_output = '''{
        "understanding_score": 20,
        "detected_concepts": ["Scrum"],
        "misconceptions": [
            "Believes Product Owner writes all the code",
            "Believes Scrum Master assigns every task"
        ],
        "evidence": "Student completely misidentifies Scrum role responsibilities."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Scrum",
        student_answer=student_answer,
        known_concepts=["Scrum"],
    )

    assert res["understanding_score"] <= 40.0
    assert len(res["misconceptions"]) >= 1


def test_i_waterfall_concept_grounding_prevents_concept_explosion():
    """Test I: Waterfall concept grounding prevents treating every mention of 'requirements', 'testing', etc. as separate curriculum concepts."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Waterfall is most appropriate for projects with stable, well-defined requirements that are unlikely to change significantly. "
        "It works well when requirements can be specified upfront and the development process can proceed through sequential phases such as requirements, design, implementation, testing, and deployment."
    )
    raw_ai_output = '''{
        "understanding_score": 90,
        "detected_concepts": ["Waterfall", "Requirements Engineering", "Functional vs Non-functional Requirements", "Agile", "Scrum", "Software Testing", "Unit Testing", "Integration Testing"],
        "misconceptions": [],
        "evidence": "Student describes Waterfall sequential stages."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Waterfall",
        student_answer=student_answer,
        known_concepts=["Waterfall", "Requirements Engineering", "Functional vs Non-functional Requirements", "Agile", "Scrum", "Software Testing", "Unit Testing", "Integration Testing"],
    )

    # Must contain ONLY Waterfall
    assert res["detected_concepts"] == ["Waterfall"]
    assert "Requirements Engineering" not in res["detected_concepts"]
    assert "Software Testing" not in res["detected_concepts"]
    assert "Agile" not in res["detected_concepts"]


def test_j_correct_functional_vs_non_functional_answer():
    """Test J: Correct Functional vs Non-functional Requirements answer must receive high score (>=80), detected_concepts = ['Functional vs Non-functional Requirements'], misconceptions = []."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Functional requirements describe what the system should do, such as allowing users to register, log in, or generate a report. "
        "Non-functional requirements describe how the system should perform, such as its security, performance, reliability, usability, and scalability."
    )
    raw_ai_output = '''{
        "understanding_score": 90,
        "detected_concepts": ["Functional vs Non-functional Requirements"],
        "misconceptions": [],
        "evidence": "Student correctly distinguishes between what the system does (functional) and how well it performs (non-functional)."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Functional vs Non-functional Requirements",
        student_answer=student_answer,
        known_concepts=["Functional vs Non-functional Requirements", "Requirements Engineering"],
    )

    assert res["understanding_score"] >= 80.0
    assert res["detected_concepts"] == ["Functional vs Non-functional Requirements"]
    assert res["misconceptions"] == []


def test_k_wrong_functional_vs_non_functional_answer():
    """Test K: Wrong Functional vs Non-functional Requirements answer (reversed definitions) must receive low score (<=40), detected_concepts = ['Functional vs Non-functional Requirements'], genuine misconception."""
    mock_client = MagicMock(spec=OllamaClient)
    analyzer = AnswerAnalyzer(ollama_client=mock_client)

    student_answer = (
        "Functional requirements describe how well a system performs, including its security, speed, and reliability, "
        "while non-functional requirements describe the specific features and actions the system must provide, such as user registration and report generation."
    )
    raw_ai_output = '''{
        "understanding_score": 75,
        "detected_concepts": ["Functional vs Non-functional Requirements"],
        "misconceptions": [],
        "evidence": "Student describes functional and non-functional requirements."
    }'''

    res = analyzer.parse_and_normalize_response(
        raw_response=raw_ai_output,
        target_concept_name="Functional vs Non-functional Requirements",
        student_answer=student_answer,
        known_concepts=["Functional vs Non-functional Requirements", "Requirements Engineering"],
    )

    assert res["understanding_score"] <= 40.0
    assert res["detected_concepts"] == ["Functional vs Non-functional Requirements"]
    assert len(res["misconceptions"]) >= 1
    assert any("revers" in m.lower() or "functional" in m.lower() or "how well" in m.lower() or "what" in m.lower() for m in res["misconceptions"])



