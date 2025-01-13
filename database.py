from fastapi import HTTPException
from models import Exercise, ExerciseAttempt
from auth_models import UserInDB, RefreshToken
from generation import generate_exercise
from bson import ObjectId
from datetime import datetime
from typing import Dict
from db import (
    exercises_collection, users_collection, attempts_collection,
    refresh_tokens_collection, exercise_cache,
    connect as connect_to_mongo,
    close as close_mongo_connection
)

# Constants
DEFAULT_CACHE_SIZE = 3  # Number of exercises to cache per user/language

async def create_exercise(exercise: Exercise):
    exercise_dict = {
        "type": exercise.type,
        "data": exercise.data.model_dump()
    }
    result = await exercises_collection.insert_one(exercise_dict)
    exercise_dict["_id"] = str(result.inserted_id)
    return exercise_dict

async def get_exercise_by_id(id: str) -> Exercise:
    try:
        exercise = await exercises_collection.find_one({"_id": ObjectId(id)})
        if exercise:
            exercise["_id"] = str(exercise["_id"])
            return exercise
        raise HTTPException(status_code=404, detail="Exercise not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

async def get_user(username: str):
    user = await users_collection.find_one({"username": username})
    if user:
        user["_id"] = str(user["_id"])
        return UserInDB.model_validate(user)
    return None

async def create_user(user: UserInDB):
    existing_user = await get_user(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user_dict = user.model_dump(exclude={"id"})
    result = await users_collection.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)
    return UserInDB.model_validate(user_dict)

async def replenish_cache(language: str, user_id: str, token: str):
    """
    Replenish the cache up to DEFAULT_CACHE_SIZE if needed
    """
    cache_count = await count_cached_exercises(language, user_id, token)
    exercises_needed = DEFAULT_CACHE_SIZE - cache_count
    
    for _ in range(exercises_needed):
        exercise = await generate_exercise(language, token)
        exercise_dict = exercise.model_dump()
        await cache_exercise(exercise_dict, language, user_id, token)

async def record_attempt(attempt: ExerciseAttempt):
    # Check if attempt already exists for this exercise and user
    existing_attempt = await attempts_collection.find_one({
        "exercise_id": attempt.exercise_id,
        "user_id": attempt.user_id
    })
    
    if existing_attempt:
        raise HTTPException(
            status_code=400,
            detail="An attempt for this exercise has already been recorded"
        )
    
    attempt_dict = attempt.model_dump()
    
    # Mark the exercise as used in the cache
    await exercise_cache.update_one(
        {
            "exercise_id": attempt.exercise_id,
            "user_id": attempt.user_id,
            "language": attempt.language,
            "used": False
        },
        {"$set": {"used": True}}
    )
    
    # Record the attempt
    result = await attempts_collection.insert_one(attempt_dict)
    attempt_dict["_id"] = str(result.inserted_id)
    return attempt_dict

async def get_user_attempts(user_id: str, language: str):
    cursor = attempts_collection.find(
        {"user_id": user_id, "language": language}
    ).sort("completed_at", -1)
    attempts = await cursor.to_list(length=None)
    for attempt in attempts:
        attempt["_id"] = str(attempt["_id"])
    return attempts 

async def store_refresh_token(refresh_token: RefreshToken):
    token_dict = refresh_token.model_dump()
    result = await refresh_tokens_collection.insert_one(token_dict)
    token_dict["_id"] = str(result.inserted_id)
    return token_dict

async def get_refresh_token(token: str):
    return await refresh_tokens_collection.find_one({"token": token, "blacklisted": False})

async def blacklist_refresh_token(token: str):
    result = await refresh_tokens_collection.update_one(
        {"token": token},
        {"$set": {"blacklisted": True}}
    )
    return result.modified_count > 0 

async def cache_exercise(exercise: dict, language: str, user_id: str, token: str):
    """
    Cache a generated exercise for future use. First stores the exercise in the exercises collection,
    then stores a reference to it in the cache.
    """
    # Ensure _id is not in the exercise dict if it exists
    if "_id" in exercise:
        del exercise["_id"]
        
    # First store the exercise
    exercise_result = await exercises_collection.insert_one(exercise)
    exercise_id = str(exercise_result.inserted_id)

    # Then store the reference in cache (without token)
    cache_doc = {
        "exercise_id": exercise_id,
        "language": language,
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "used": False
    }
    await exercise_cache.insert_one(cache_doc)

async def count_cached_exercises(language: str, user_id: str, token: str) -> int:
    """
    Count unused cached exercises for a specific user and language
    """
    return await exercise_cache.count_documents({
        "language": language,
        "user_id": user_id,
        "used": False
    }) 

async def delete_exercise_cache(language: str, user_id: str):
    """
    Delete all cached exercises for a specific user and language.
    Also removes the exercises from the exercises collection.
    """
    # First get all cached exercises for this user/language
    cached_exercises = await exercise_cache.find({
        "language": language,
        "user_id": user_id
    }).to_list(length=None)
    
    # Delete the exercises from exercises collection
    exercise_ids = [ObjectId(ex["exercise_id"]) for ex in cached_exercises]
    if exercise_ids:
        await exercises_collection.delete_many({"_id": {"$in": exercise_ids}})
    
    # Delete from cache
    result = await exercise_cache.delete_many({
        "language": language,
        "user_id": user_id
    })
    
    return result.deleted_count

async def regenerate_exercise_cache(language: str, user_id: str, token: str, target_count: int = DEFAULT_CACHE_SIZE):
    """
    Regenerate the exercise cache for a specific user and language up to target_count.
    First deletes existing cache, then generates new exercises.
    """
    # First delete existing cache
    await delete_exercise_cache(language, user_id)
    
    # Generate new exercises up to target count
    for _ in range(target_count):
        exercise = await generate_exercise(language, token)
        exercise_dict = exercise.model_dump()
        await cache_exercise(exercise_dict, language, user_id, token)
    
    return await count_cached_exercises(language, user_id, token) 

async def get_all_cached_exercises(language: str, user_id: str):
    """
    Get all unused cached exercises for a specific user and language
    """
    # Find all unused exercises
    cursor = exercise_cache.find(
        {
            "language": language,
            "user_id": user_id,
            "used": False
        },
        sort=[("created_at", 1)]  # Get oldest first
    )
    
    cache_docs = await cursor.to_list(length=None)
    exercises = []
    
    # Fetch each exercise from exercises collection
    for doc in cache_docs:
        exercise = await exercises_collection.find_one({"_id": ObjectId(doc["exercise_id"])})
        if exercise:
            exercise = dict(exercise)  # Convert from MongoDB document to dict
            exercise["_id"] = str(exercise["_id"])
            exercises.append(exercise)
    
    return exercises 