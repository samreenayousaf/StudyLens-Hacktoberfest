from sqlalchemy.orm import Session
from app.models import Concept, Question

SEED_CONCEPTS = [
    {
        "name": "Requirements Engineering",
        "description": "Principles and practices of capturing, analyzing, documenting, and managing software requirements.",
    },
    {
        "name": "Functional vs Non-functional Requirements",
        "description": "Distinguishing what a system should do versus how well it should perform or operate.",
    },
    {
        "name": "Agile",
        "description": "Iterative and incremental software development methodologies emphasizing flexibility and user feedback.",
    },
    {
        "name": "Scrum",
        "description": "An Agile framework centered on sprints, daily standups, and incremental product increments.",
    },
    {
        "name": "Waterfall",
        "description": "A sequential linear software development process model.",
    },
    {
        "name": "Coupling",
        "description": "The degree of interdependence between software modules.",
    },
    {
        "name": "Cohesion",
        "description": "The degree to which elements inside a module belong together.",
    },
    {
        "name": "Software Testing",
        "description": "Processes for evaluating and verifying that a software product does what it is supposed to do.",
    },
    {
        "name": "Unit Testing",
        "description": "Testing individual components or functions of code in isolation.",
    },
    {
        "name": "Integration Testing",
        "description": "Testing interactions between integrated modules or services.",
    },
    {
        "name": "Version Control",
        "description": "Tracking and managing changes to software code over time.",
    },
]

SEED_QUESTIONS = {
    "Coupling": [
        "What is meant by high coupling in software design?",
        "Which situation represents high coupling between two software modules, and why is it usually undesirable?",
        "How can a software developer reduce coupling between modules?",
        "What is the difference between high coupling and low coupling in software design?",
        "Why does low coupling generally make software easier to maintain, test, and modify?",
    ],
    "Requirements Engineering": [
        "What is the primary objective of requirements engineering in software development?",
    ],
    "Functional vs Non-functional Requirements": [
        "How do functional requirements differ from non-functional requirements in software specifications?",
    ],
    "Agile": [
        "What are the core principles of the Agile Manifesto regarding software development?",
    ],
    "Scrum": [
        "What are the primary roles defined in the Scrum framework and their main responsibilities?",
    ],
    "Waterfall": [
        "In what types of software projects is the Waterfall development model most appropriate?",
    ],
    "Cohesion": [
        "What is the difference between high cohesion and low cohesion in software module design?",
    ],
    "Software Testing": [
        "Why is software testing essential throughout the software development lifecycle?",
    ],
    "Unit Testing": [
        "What characterizes an effective unit test in automated test suites?",
    ],
    "Integration Testing": [
        "What is the primary goal of integration testing compared to unit testing?",
    ],
    "Version Control": [
        "Why is version control critical for collaborative software engineering teams?",
    ],
}


def seed_database(db: Session) -> None:
    """Idempotently seed concepts and questions without deleting or modifying existing data."""
    concept_map = {}

    # Seed concepts idempotently
    for c_data in SEED_CONCEPTS:
        existing_concept = db.query(Concept).filter(Concept.name == c_data["name"]).first()
        if existing_concept:
            concept_map[c_data["name"]] = existing_concept
        else:
            new_concept = Concept(
                name=c_data["name"],
                description=c_data["description"],
                is_active=True,
            )
            db.add(new_concept)
            db.flush()
            concept_map[c_data["name"]] = new_concept

    db.commit()

    # Seed questions idempotently
    for concept_name, questions_list in SEED_QUESTIONS.items():
        concept = concept_map.get(concept_name)
        if not concept:
            continue

        for q_text in questions_list:
            existing_question = (
                db.query(Question)
                .filter(
                    Question.concept_id == concept.id,
                    Question.question_text == q_text,
                )
                .first()
            )
            if not existing_question:
                new_question = Question(
                    concept_id=concept.id,
                    question_text=q_text,
                    difficulty="medium",
                    question_type="open_ended",
                    is_active=True,
                )
                db.add(new_question)

    db.commit()
