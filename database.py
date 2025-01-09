from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from models import Exercise, ExerciseAttempt
from auth_models import UserInDB, RefreshToken
import logging
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict

logger = logging.getLogger("uvicorn")

# Load environment variables
load_dotenv("secret.env")

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

async def get_exercise_by_id(id: str):
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
    attempt_dict = attempt.model_dump()
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