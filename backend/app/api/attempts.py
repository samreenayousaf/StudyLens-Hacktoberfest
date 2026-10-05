from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.mastery_service import record_attempt_and_update_mastery
from app.schemas import AttemptCreate, AttemptSubmitResponse

router = APIRouter()


@router.post("/attempts", response_model=AttemptSubmitResponse, status_code=status.HTTP_201_CREATED)
def submit_attempt(
    payload: AttemptCreate,
    db: Session = Depends(get_db),
):
    """Submit a student answer attempt, record it, and update/create the mastery level."""
    attempt, mastery = record_attempt_and_update_mastery(
        db=db,
        question_id=payload.question_id,
        answer_text=payload.answer_text,
        understanding_score=payload.understanding_score,
        correct=payload.correct,
    )
    return AttemptSubmitResponse(attempt=attempt, mastery=mastery)
