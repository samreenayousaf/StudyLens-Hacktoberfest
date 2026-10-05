from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Attempt, Mastery, Question


def should_retest(
    mastery_level: str,
    misconceptions: Optional[List[str]] = None,
    understanding_score: Optional[float] = None,
) -> Tuple[bool, str]:
    """Determine whether a retest is required based on current AI evaluation and mastery level.

    Retest Rules:
    1. If current AI understanding_score < 60.0 -> Retest required.
    2. OR if current AI analysis contains meaningful misconceptions -> Retest required.
    3. Otherwise, fallback to existing mastery level rules:
       - Weak (0-39.9): Retest required.
       - Developing (40-59.9): Retest required if misconceptions exist (handled above).
       - Proficient (60-79.9): No immediate retest.
       - Strong (80-100): No immediate retest.
    """
    misc_list = [str(m).strip() for m in (misconceptions or []) if m and str(m).strip()]

    if understanding_score is not None and float(understanding_score) < 60.0:
        return True, f"Current answer understanding score ({float(understanding_score):.1f}) is below threshold (60.0). Retest is required."

    if misc_list:
        misc_str = ", ".join(misc_list)
        return True, f"Identified misconceptions in answer: {misc_str}."

    level = (mastery_level or "").lower()

    if level == "weak":
        return True, "Concept mastery level is weak. Retest is required."
    elif level == "developing":
        return False, "Concept is developing with no immediate misconceptions."
    elif level == "proficient":
        return False, "Concept mastery level is proficient. No immediate retest required."
    elif level == "strong":
        return False, "Concept mastery level is strong. No immediate retest required."
    else:
        return False, "No retest required."
    

def select_retest_question(db: Session, concept_id: int) -> Optional[Question]:
    """Select a targeted retest question belonging to the given concept.

    Selection Strategy:
    1. Select active questions belonging strictly to concept_id.
    2. Prefer an active question that has NOT been attempted yet.
    3. If multiple unanswered questions exist, select deterministically (lowest question.id).
    4. If all questions for that concept have been attempted, fallback deterministically
       to the most recently attempted active question for that concept.
    """
    concept_questions = (
        db.query(Question)
        .filter(
            Question.concept_id == concept_id,
            Question.is_active.is_(True),
        )
        .order_by(Question.id)
        .all()
    )

    if not concept_questions:
        return None

    # Find active questions with 0 attempts
    unattempted_questions = []
    for q in concept_questions:
        attempt_exists = (
            db.query(Attempt.id)
            .filter(Attempt.question_id == q.id)
            .first()
        )
        if not attempt_exists:
            unattempted_questions.append(q)

    if unattempted_questions:
        # Deterministically select the first unanswered question
        return unattempted_questions[0]

    # Fallback if all active questions have been attempted:
    # Select the most recently attempted active question for this concept
    most_recent_attempt = (
        db.query(Attempt)
        .filter(Attempt.concept_id == concept_id)
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .first()
    )
    if most_recent_attempt:
        fallback_q = (
            db.query(Question)
            .filter(
                Question.id == most_recent_attempt.question_id,
                Question.is_active.is_(True),
            )
            .first()
        )
        if fallback_q:
            return fallback_q

    # Absolute fallback to first active question in list
    return concept_questions[0]


def get_next_retest(
    db: Session,
    last_concept_id: Optional[int] = None,
    misconceptions: Optional[List[str]] = None,
    understanding_score: Optional[float] = None,
) -> Dict[str, Any]:
    """Determine next retest payload for a concept or overall session."""
    no_retest_payload = {
        "required": False,
        "reason": "No retest currently required.",
        "question_id": None,
        "question_text": None,
        "concept_id": None,
        "concept": None,
    }

    # Case A: Explicit concept check (e.g. from just-completed attempt)
    if last_concept_id is not None:
        mastery = db.query(Mastery).filter(Mastery.concept_id == last_concept_id).first()
        if not mastery:
            return no_retest_payload

        required, reason = should_retest(
            mastery_level=mastery.mastery_level,
            misconceptions=misconceptions or [],
            understanding_score=understanding_score,
        )
        if not required:
            return {
                "required": False,
                "reason": reason,
                "question_id": None,
                "question_text": None,
                "concept_id": mastery.concept_id,
                "concept": mastery.concept.name if mastery.concept else None,
            }

        retest_q = select_retest_question(db, last_concept_id)
        if not retest_q:
            return no_retest_payload

        return {
            "required": True,
            "reason": reason,
            "question_id": retest_q.id,
            "question_text": retest_q.question_text,
            "concept_id": retest_q.concept_id,
            "concept": retest_q.concept.name if retest_q.concept else None,
        }

    # Case B: Global check for GET /api/retest/next
    # Find assessed concepts that require a retest, prioritizing weak concepts first
    assessed_masteries = (
        db.query(Mastery)
        .filter(Mastery.attempts_count > 0)
        .order_by(Mastery.updated_at.desc())
        .all()
    )

    for m in assessed_masteries:
        # Check if weak (weak concepts always require retest)
        required, reason = should_retest(m.mastery_level, [])
        if required:
            retest_q = select_retest_question(db, m.concept_id)
            if retest_q:
                return {
                    "required": True,
                    "reason": reason,
                    "question_id": retest_q.id,
                    "question_text": retest_q.question_text,
                    "concept_id": retest_q.concept_id,
                    "concept": retest_q.concept.name if retest_q.concept else None,
                }

    return no_retest_payload
