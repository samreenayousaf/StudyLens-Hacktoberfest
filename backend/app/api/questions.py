from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Attempt, Concept, Question
from app.schemas import QuestionResponse

router = APIRouter()


@router.get("/questions", response_model=List[QuestionResponse])
def get_questions(
    concept_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Retrieve active questions, optionally filtered by concept_id."""
    query = db.query(Question).filter(Question.is_active.is_(True))
    if concept_id is not None:
        query = query.filter(Question.concept_id == concept_id)
    return query.order_by(Question.id).all()


@router.get("/questions/initial", response_model=QuestionResponse)
def get_initial_question(db: Session = Depends(get_db)):
    """Retrieve the initial question for a student session.
    
    Prefers active concepts that have not yet been assessed (0 attempts).
    Deterministically selects an unattempted question for that concept.
    """
    active_concepts = (
        db.query(Concept)
        .filter(Concept.is_active.is_(True))
        .order_by(Concept.id)
        .all()
    )

    if not active_concepts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active concepts available.",
        )

    # Calculate attempt counts per concept
    unassessed_concept = None
    least_attempted_concept = None
    min_attempts = float("inf")

    for concept in active_concepts:
        attempt_count = (
            db.query(func.count(Attempt.id))
            .filter(Attempt.concept_id == concept.id)
            .scalar()
        ) or 0

        if attempt_count == 0 and unassessed_concept is None:
            unassessed_concept = concept
            break

        if attempt_count < min_attempts:
            min_attempts = attempt_count
            least_attempted_concept = concept

    target_concept = unassessed_concept or least_attempted_concept

    if not target_concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No concepts found.",
        )

    # Get active questions for the target concept
    concept_questions = (
        db.query(Question)
        .filter(
            Question.concept_id == target_concept.id,
            Question.is_active.is_(True),
        )
        .order_by(Question.id)
        .all()
    )

    if not concept_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active questions found for concept '{target_concept.name}'.",
        )

    # Find first unattempted question for this concept
    for question in concept_questions:
        attempted = (
            db.query(Attempt.id)
            .filter(Attempt.question_id == question.id)
            .first()
        )
        if not attempted:
            return question

    # Fallback to the first active question if all have been attempted
    return concept_questions[0]
