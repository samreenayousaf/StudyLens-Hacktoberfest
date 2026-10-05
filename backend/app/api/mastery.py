from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Mastery
from app.schemas import MasteryResponse

router = APIRouter()


@router.get("/mastery", response_model=List[MasteryResponse])
def get_mastery(db: Session = Depends(get_db)):
    """Retrieve mastery records for all assessed concepts."""
    return (
        db.query(Mastery)
        .filter(Mastery.attempts_count > 0)
        .order_by(Mastery.concept_id)
        .all()
    )


@router.get("/mastery/weak", response_model=List[MasteryResponse])
def get_weak_mastery(db: Session = Depends(get_db)):
    """Retrieve mastery records for assessed concepts whose mastery level is 'weak'.
    Unassessed concepts are strictly excluded.
    """
    return (
        db.query(Mastery)
        .filter(
            Mastery.mastery_level == "weak",
            Mastery.attempts_count > 0,
        )
        .order_by(Mastery.concept_id)
        .all()
    )
