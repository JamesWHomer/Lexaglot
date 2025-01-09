from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from models import Exercise, ExerciseAttempt
import database
from auth_router import router as auth_router
from auth import get_current_active_user
from auth_models import User
from typing import Dict, Any, Optional
from datetime import datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.connect_to_mongo()
    yield
    # Shutdown
    await database.close_mongo_connection()

app = FastAPI(
    title="Lexaglot API",
    description="API for Lexaglot language learning application",
    version="1.0.0",
    lifespan=lifespan
)

# Include authentication router
app.include_router(auth_router, tags=["authentication"])

@app.post("/exercise")
async def create_exercise(exercise: Exercise):
    """Create a new exercise (AI-generated, single-use)"""
    return await database.create_exercise(exercise)

@app.get("/exercise/{id}")
async def get_exercise(id: str):
    """Get a specific exercise by ID"""
    return await database.get_exercise_by_id(id)

@app.post("/exercise-attempt/{exercise_id}")
async def record_attempt(
    exercise_id: str,
    language: str,
    time_spent_ms: int,
    user_response: Any,
    current_user: User = Depends(get_current_active_user)
):
    """
    Record a user's attempt at an exercise.
    - time_spent_ms: how long the exercise took in milliseconds
    - user_response: the raw response data from the app (format depends on exercise type)
    """
    attempt = ExerciseAttempt(
        user_id=str(current_user.id),
        exercise_id=exercise_id,
        language=language,
        completed_at=datetime.utcnow(),
        time_spent_ms=time_spent_ms,
        user_response=user_response
    )
    
    return await database.record_attempt(attempt)

@app.get("/user-attempts/{language}")
async def get_user_attempts(
    language: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get all of a user's exercise attempts for a specific language"""
    return await database.get_user_attempts(str(current_user.id), language)

@app.get("/tokenbank/{language}")
async def get_tokenbank(
    language: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, int]:
    """Get the user's token bank for a specific language"""
    return await database.get_user_tokenbank(str(current_user.id), language)

@app.put("/tokenbank/{language}")
async def update_tokenbank(
    language: str,
    tokens: Dict[str, int],
    current_user: User = Depends(get_current_active_user)
):
    """Update the entire token bank for a specific language"""
    success = await database.set_user_tokenbank(str(current_user.id), language, tokens)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update token bank")
    return {"status": "success"}

@app.patch("/tokenbank/{language}/{token}")
async def update_token(
    language: str,
    token: str,
    count: int,
    current_user: User = Depends(get_current_active_user)
):
    """Update the count for a specific token"""
    success = await database.update_token_count(str(current_user.id), language, token, count)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update token count")
    return {"status": "success"}