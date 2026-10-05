from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import models so SQLAlchemy metadata registers all tables
import app.models
from app.api.ai import router as ai_router
from app.api.attempts import router as attempts_router
from app.api.concepts import router as concepts_router
from app.api.health import router as health_router
from app.api.learning import router as learning_router
from app.api.mastery import router as mastery_router
from app.api.questions import router as questions_router
from app.api.retest import router as retest_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables are created on startup
    Base.metadata.create_all(bind=engine)

    # Run idempotent seeding
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(health_router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(concepts_router, prefix=settings.API_V1_STR, tags=["Concepts"])
app.include_router(questions_router, prefix=settings.API_V1_STR, tags=["Questions"])
app.include_router(attempts_router, prefix=settings.API_V1_STR, tags=["Attempts"])
app.include_router(mastery_router, prefix=settings.API_V1_STR, tags=["Mastery"])
app.include_router(ai_router, prefix=settings.API_V1_STR, tags=["AI Analysis"])
app.include_router(retest_router, prefix=settings.API_V1_STR, tags=["Retest"])
app.include_router(learning_router, prefix=settings.API_V1_STR, tags=["Learning Loop"])


@app.get("/")
def root():
    return {"message": "StudyLens API is running. Check /api/health for system status."}
