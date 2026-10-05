from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "StudyLens API"


class ConceptBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class ConceptCreate(ConceptBase):
    pass


class ConceptResponse(ConceptBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class QuestionBase(BaseModel):
    concept_id: int
    question_text: str
    difficulty: str = "medium"
    question_type: str = "open_ended"
    is_active: bool = True


class QuestionCreate(QuestionBase):
    pass


class QuestionResponse(QuestionBase):
    id: int
    question_id: int
    concept_id: int
    question_text: str
    difficulty: str = "medium"
    question_type: str = "open_ended"
    is_active: bool = True
    created_at: datetime
    concept: Optional[ConceptResponse] = None

    model_config = ConfigDict(from_attributes=True)


class AttemptBase(BaseModel):
    question_id: int
    concept_id: int
    answer_text: str
    understanding_score: Optional[float] = None
    correct: bool


class AttemptCreate(BaseModel):
    question_id: int
    answer_text: str
    understanding_score: float = Field(..., ge=0.0, le=100.0)
    correct: Optional[bool] = None


class AttemptResponse(AttemptBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MasteryBase(BaseModel):
    concept_id: int
    mastery_score: float = 0.0
    mastery_level: str = "weak"
    attempts_count: int = 0
    correct_count: int = 0


class MasteryResponse(MasteryBase):
    id: int
    updated_at: datetime
    concept: Optional[ConceptResponse] = None

    model_config = ConfigDict(from_attributes=True)


class AttemptSubmitResponse(BaseModel):
    attempt: AttemptResponse
    mastery: MasteryResponse


class AIAnalysisRequest(BaseModel):
    question_id: int
    answer_text: str


class AIAnalysisResponse(BaseModel):
    understanding_score: float
    detected_concepts: List[str]
    misconceptions: List[str]
    evidence: str


class RetestResponse(BaseModel):
    required: bool
    reason: str
    question_id: Optional[int] = None
    question_text: Optional[str] = None
    concept_id: Optional[int] = None
    concept: Optional[str] = None


class LearningSubmitRequest(BaseModel):
    question_id: int
    answer_text: str


class LearningSubmitResponse(BaseModel):
    analysis: AIAnalysisResponse
    attempt: AttemptResponse
    mastery: MasteryResponse
    retest: RetestResponse
