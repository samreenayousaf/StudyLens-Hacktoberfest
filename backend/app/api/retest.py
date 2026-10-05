from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.retest_service import get_next_retest
from app.schemas import RetestResponse

router = APIRouter()


@router.get("/retest/next", response_model=RetestResponse)
def get_retest_next(db: Session = Depends(get_db)):
    """Determine whether a targeted retest is currently required for the student."""
    res = get_next_retest(db)
    return RetestResponse(**res)
