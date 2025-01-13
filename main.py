from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
from models import Exercise, ExerciseAttempt
import database
from database import DEFAULT_CACHE_SIZE
from auth_router import router as auth_router
from auth import get_current_active_user
from auth_models import User
from typing import Dict, Any, Optional
from datetime import datetime
import random 
from generation import generate_exercise
from recommendation import get_next_token
from tokenbank import get_user_tokenbank, set_user_tokenbank, update_token_count

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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Record a user's attempt at an exercise.
    - time_spent_ms: how long the exercise took in milliseconds
    - user_response: the raw response data from the app (format depends on exercise type)
    """
    # Record the attempt
    attempt = ExerciseAttempt(
        user_id=str(current_user.id),
        exercise_id=exercise_id,
        language=language,
        completed_at=datetime.utcnow(),
        time_spent_ms=time_spent_ms,
        user_response=user_response
    )
    
    result = await database.record_attempt(attempt)
    
    # Get the current token for replenishment
    token = await get_next_token(str(current_user.id), language)
    if token:
        background_tasks.add_task(
            database.replenish_cache,
            language,
            str(current_user.id),
            token
        )
    
    return result

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
    return await get_user_tokenbank(str(current_user.id), language)

@app.get("/next_exercise")
async def next_exercise(
    language: str,
    current_user: User = Depends(get_current_active_user)
): 
    # Get the next token for this user and language
    token = await get_next_token(str(current_user.id), language)
    if not token:
        raise HTTPException(status_code=404, detail="No tokens available for practice")
    
    # Try to get a cached exercise
    cached_exercise = await database.get_cached_exercise(language, str(current_user.id), token)
    if cached_exercise:
        return cached_exercise
        
    # If no cached exercise, generate one and cache it
    exercise = await generate_exercise(language, token)
    exercise_dict = exercise.model_dump(by_alias=True)
    
    await database.cache_exercise(
        exercise_dict,
        language,
        str(current_user.id),
        token
    )
    
    # Return the exercise from the database to ensure proper serialization
    return await database.get_exercise_by_id(exercise_dict["_id"])

@app.put("/tokenbank/{language}")
async def update_tokenbank(
    language: str,
    tokens: Dict[str, int],
    current_user: User = Depends(get_current_active_user)
):
    """Update the entire token bank for a specific language"""
    success = await set_user_tokenbank(str(current_user.id), language, tokens)
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
    success = await update_token_count(str(current_user.id), language, token, count)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update token count")
    return {"status": "success"}

@app.delete("/exercise-cache/{language}")
async def clear_exercise_cache(
    language: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete all cached exercises for the current user and language"""
    deleted_count = await database.delete_exercise_cache(language, str(current_user.id))
    return {"deleted_count": deleted_count}

@app.post("/exercise-cache/{language}/regenerate")
async def regenerate_cache(
    language: str,
    current_user: User = Depends(get_current_active_user)
):
    """Regenerate the exercise cache for the current user and language"""
    # Get the next token for this user and language
    token = await get_next_token(str(current_user.id), language)
    if not token:
        raise HTTPException(status_code=404, detail="No tokens available for practice")
    
    count = await database.regenerate_exercise_cache(language, str(current_user.id), token)
    return {"cached_exercises": count}