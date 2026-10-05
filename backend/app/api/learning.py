from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.ai.analyzer import AnswerAnalyzer
from app.database import get_db
from app.mastery_service import record_attempt_and_update_mastery
from app.models import Attempt, Concept, Mastery, Question
from app.retest_service import get_next_retest
from app.schemas import (
    AIAnalysisResponse,
    LearningSubmitRequest,
    LearningSubmitResponse,
    RetestResponse,
)

router = APIRouter()


@router.post("/learning/submit-answer", response_model=LearningSubmitResponse, status_code=status.HTTP_200_OK)
def submit_learning_answer(
    payload: LearningSubmitRequest,
    db: Session = Depends(get_db),
):
    """Full adaptive learning loop endpoint:
    1. Validate question & concept.
    2. Duplicate submission protection check.
    3. Local AI analysis (Gemma 3:1B via Ollama).
    4. Deterministic Attempt & Mastery update.
    5. Targeted retest evaluation & next question selection.
    """
    question = (
        db.query(Question)
        .filter(Question.id == payload.question_id, Question.is_active.is_(True))
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active question with id {payload.question_id} not found.",
        )

    target_concept = question.concept
    if not target_concept or not target_concept.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question target concept is missing or inactive.",
        )

    # Server-side protection against rapid duplicate submission
    now_utc = datetime.now(timezone.utc)
    recent_cutoff = now_utc - timedelta(seconds=5)
    recent_attempt = (
        db.query(Attempt)
        .filter(
            Attempt.question_id == payload.question_id,
            Attempt.answer_text == payload.answer_text,
            Attempt.created_at >= recent_cutoff,
        )
        .order_by(Attempt.created_at.desc())
        .first()
    )

    if recent_attempt:
        # Deduplicated response: return existing attempt & current mastery
        mastery = (
            db.query(Mastery)
            .filter(Mastery.concept_id == target_concept.id)
            .first()
        )
        retest_info = get_next_retest(db, last_concept_id=target_concept.id)
        return LearningSubmitResponse(
            analysis=AIAnalysisResponse(
                understanding_score=recent_attempt.understanding_score or 50.0,
                detected_concepts=[target_concept.name],
                misconceptions=[],
                evidence="Duplicate submission detected; returning recent attempt analysis.",
            ),
            attempt=recent_attempt,
            mastery=mastery,
            retest=RetestResponse(**retest_info),
        )

    # 1. Known active concepts list
    known_active_concepts = [
        c.name
        for c in db.query(Concept).filter(Concept.is_active.is_(True)).order_by(Concept.id).all()
    ]

    # 2. Local AI Answer Analysis via Ollama + Gemma 3:1B
    analyzer = AnswerAnalyzer()
    ai_result = analyzer.analyze(
        question_text=question.question_text,
        target_concept_name=target_concept.name,
        target_concept_description=target_concept.description or "",
        student_answer=payload.answer_text,
        known_concepts=known_active_concepts,
    )

    # 3. Deterministic Attempt & Mastery engine update
    attempt, mastery = record_attempt_and_update_mastery(
        db=db,
        question_id=payload.question_id,
        answer_text=payload.answer_text,
        understanding_score=ai_result["understanding_score"],
        correct=None,  # Automatically evaluated >= 60.0
    )

    # 4. Evaluate whether targeted retest is required & select next question
    retest_data = get_next_retest(
        db=db,
        last_concept_id=target_concept.id,
        misconceptions=ai_result["misconceptions"],
        understanding_score=ai_result["understanding_score"],
    )

    return LearningSubmitResponse(
        analysis=AIAnalysisResponse(
            understanding_score=ai_result["understanding_score"],
            detected_concepts=ai_result["detected_concepts"],
            misconceptions=ai_result["misconceptions"],
            evidence=ai_result["evidence"],
        ),
        attempt=attempt,
        mastery=mastery,
        retest=RetestResponse(**retest_data),
    )
