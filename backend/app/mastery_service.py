from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Attempt, Mastery, Question


def get_mastery_level(score: float) -> str:
    """Determine the mastery level based on score:
    0–39: weak
    40–59: developing
    60–79: proficient
    80–100: strong
    """
    clamped_score = max(0.0, min(100.0, float(score)))
    if clamped_score < 40.0:
        return "weak"
    elif clamped_score < 60.0:
        return "developing"
    elif clamped_score < 80.0:
        return "proficient"
    else:
        return "strong"


def calculate_mastery(previous_mastery: Optional[float], current_understanding: float) -> float:
    """Calculate the new mastery score.
    First assessment: returns current_understanding clamped to [0, 100].
    Subsequent assessments: (previous_mastery * 0.70) + (current_understanding * 0.30), clamped to [0, 100].
    """
    current_clamped = max(0.0, min(100.0, float(current_understanding)))
    if previous_mastery is None:
        return current_clamped

    prev_clamped = max(0.0, min(100.0, float(previous_mastery)))
    new_score = (prev_clamped * 0.70) + (current_clamped * 0.30)
    return max(0.0, min(100.0, new_score))


def record_attempt_and_update_mastery(
    db: Session,
    question_id: int,
    answer_text: str,
    understanding_score: float,
    correct: Optional[bool] = None,
) -> Tuple[Attempt, Mastery]:
    """Validate question, record attempt, and update/create corresponding mastery record."""
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.is_active.is_(True))
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active question with id {question_id} not found.",
        )

    concept_id = question.concept_id

    # Determine correctness: default to understanding_score >= 60.0 if correct is not explicitly specified
    is_correct = correct if correct is not None else (understanding_score >= 60.0)

    # Create Attempt
    attempt = Attempt(
        question_id=question_id,
        concept_id=concept_id,
        answer_text=answer_text,
        understanding_score=understanding_score,
        correct=is_correct,
    )
    db.add(attempt)

    # Query or create Mastery for this concept
    mastery = db.query(Mastery).filter(Mastery.concept_id == concept_id).first()

    if mastery is None:
        # First assessment for this concept
        new_score = calculate_mastery(None, understanding_score)
        new_level = get_mastery_level(new_score)
        mastery = Mastery(
            concept_id=concept_id,
            mastery_score=new_score,
            mastery_level=new_level,
            attempts_count=1,
            correct_count=1 if is_correct else 0,
        )
        db.add(mastery)
    else:
        # Subsequent assessment
        new_score = calculate_mastery(mastery.mastery_score, understanding_score)
        mastery.mastery_score = new_score
        mastery.mastery_level = get_mastery_level(new_score)
        mastery.attempts_count += 1
        if is_correct:
            mastery.correct_count += 1
        mastery.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(attempt)
    db.refresh(mastery)
    return attempt, mastery
