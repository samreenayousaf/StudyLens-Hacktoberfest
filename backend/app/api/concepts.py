from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Concept
from app.schemas import ConceptResponse

router = APIRouter()


@router.get("/concepts", response_model=List[ConceptResponse])
def get_concepts(db: Session = Depends(get_db)):
    """Retrieve all active concepts."""
    return db.query(Concept).filter(Concept.is_active.is_(True)).order_by(Concept.id).all()
