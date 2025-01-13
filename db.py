from motor.motor_asyncio import AsyncIOMotorClient
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger("uvicorn")

# Load environment variables
load_dotenv("secret.env")

MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    logger.error("MONGODB_URL environment variable is not set")
    exit(1)

client = AsyncIOMotorClient(MONGODB_URL)
db = client.lexaglot

# Collections
exercises_collection = db.exercises
users_collection = db.users
attempts_collection = db.attempts
refresh_tokens_collection = db.refresh_tokens
tokenbank_collection = db.tokenbank
exercise_cache = db.exercise_cache

async def connect():
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

async def close():
    client.close() 