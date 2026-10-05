from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    questions = relationship("Question", back_populates="concept", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="concept", cascade="all, delete-orphan")
    mastery = relationship("Mastery", back_populates="concept", uselist=False, cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    difficulty = Column(String(50), default="medium", nullable=False)
    question_type = Column(String(50), default="open_ended", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    concept = relationship("Concept", back_populates="questions")
    attempts = relationship("Attempt", back_populates="question", cascade="all, delete-orphan")

    @property
    def question_id(self) -> int:
        return self.id


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    understanding_score = Column(Float, nullable=True)
    correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    question = relationship("Question", back_populates="attempts")
    concept = relationship("Concept", back_populates="attempts")


class Mastery(Base):
    __tablename__ = "mastery"

    id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), unique=True, nullable=False, index=True)
    mastery_score = Column(Float, default=0.0, nullable=False)
    mastery_level = Column(String(50), default="weak", nullable=False)
    attempts_count = Column(Integer, default=0, nullable=False)
    correct_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    concept = relationship("Concept", back_populates="mastery")
