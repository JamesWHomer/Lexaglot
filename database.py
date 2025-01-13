from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from models import Exercise, ExerciseAttempt
from auth_models import UserInDB, RefreshToken
import logging
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger("uvicorn")

# Load environment variables
load_dotenv("secret.env")

# Constants
DEFAULT_CACHE_SIZE = 3  # Number of exercises to cache per user/language

MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    logger.error("MONGODB_URL environment variable is not set")
    exit(1)

client = AsyncIOMotorClient(MONGODB_URL)
db = client.lexaglot
exercises_collection = db.exercises
users_collection = db.users
attempts_collection = db.attempts
refresh_tokens_collection = db.refresh_tokens
tokenbank = db.tokenbank
exercise_cache = db.exercise_cache

async def connect_to_mongo():
    try:
        await client.admin.command('ping')
        # Create unique index on username
        await users_collection.create_index("username", unique=True)
        # Create TTL index for refresh tokens
        await refresh_tokens_collection.create_index("expires_at", expireAfterSeconds=0)
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        exit(1)

async def close_mongo_connection():
    client.close()

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

async def get_user_tokenbank(user_id: str, language: str) -> Dict[str, int]:
    """
    Retrieve the tokenbank for a specific user and language
    
    Args:
        user_id (str): The ID of the user
        language (str): The language code
        
    Returns:
        Dict[str, int]: A dictionary mapping tokens to their counts
    """
    result = await tokenbank.find_one({"user_id": user_id, "language": language})
    if result:
        # Remove MongoDB-specific fields and return only the tokens
        return result.get("tokens", {})
    return {} 

async def set_user_tokenbank(user_id: str, language: str, tokens: Dict[str, int]) -> bool:
    """
    Set or update the tokenbank for a specific user and language
    
    Args:
        user_id (str): The ID of the user
        language (str): The language code
        tokens (Dict[str, int]): Dictionary mapping tokens to their counts
        
    Returns:
        bool: True if the operation was successful
    """
    result = await tokenbank.update_one(
        {"user_id": user_id, "language": language},
        {"$set": {"tokens": tokens}},
        upsert=True
    )
    return result.acknowledged 

async def update_token_count(user_id: str, language: str, token: str, count: int) -> bool:
    """
    Update or set the count for a specific token in user's tokenbank
    
    Args:
        user_id (str): The ID of the user
        language (str): The language code
        token (str): The token to update
        count (int): The new count value
        
    Returns:
        bool: True if the operation was successful
    """
    result = await tokenbank.update_one(
        {"user_id": user_id, "language": language},
        {"$set": {f"tokens.{token}": count}},
        upsert=True
    )
    return result.acknowledged 

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

async def get_cached_exercise(language: str, user_id: str, token: str):
    """
    Get the oldest unused exercise from the cache for specific user and language
    """
    # Find the oldest unused exercise without marking it as used
    result = await exercise_cache.find_one(
        {
            "language": language,
            "user_id": user_id,
            "used": False
        },
        sort=[("created_at", 1)]  # Get oldest first
    )
    
    if result:
        # Fetch the actual exercise from exercises collection
        exercise = await exercises_collection.find_one({"_id": ObjectId(result["exercise_id"])})
        if exercise:
            # Convert ObjectId to string before returning
            exercise = dict(exercise)  # Convert from MongoDB document to dict
            exercise["_id"] = str(exercise["_id"])
            return exercise
    return None

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