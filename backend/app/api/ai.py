from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.ai.analyzer import AnswerAnalyzer
from app.database import get_db
from app.models import Concept, Question
from app.schemas import AIAnalysisRequest, AIAnalysisResponse

router = APIRouter()


@router.post("/ai/analyze-answer", response_model=AIAnalysisResponse, status_code=status.HTTP_200_OK)
def analyze_answer(
    payload: AIAnalysisRequest,
    db: Session = Depends(get_db),
):
    """Analyze a student's answer using local AI (Gemma 3:1B via Ollama).
    
    IMPORTANT: This endpoint strictly analyzes answer text.
    It DOES NOT create Attempt records, update Mastery, or modify database state.
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

    known_active_concepts = [
        c.name
        for c in db.query(Concept).filter(Concept.is_active.is_(True)).order_by(Concept.id).all()
    ]

    analyzer = AnswerAnalyzer()
    analysis_result = analyzer.analyze(
        question_text=question.question_text,
        target_concept_name=target_concept.name,
        target_concept_description=target_concept.description or "",
        student_answer=payload.answer_text,
        known_concepts=known_active_concepts,
    )

    return AIAnalysisResponse(
        understanding_score=analysis_result["understanding_score"],
        detected_concepts=analysis_result["detected_concepts"],
        misconceptions=analysis_result["misconceptions"],
        evidence=analysis_result["evidence"],
    )
