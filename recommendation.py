from auth_models import User
from database import get_user_tokenbank, set_user_tokenbank
from typing import Optional
import asyncio
import random

async def get_next_token(user_id: Optional[str], language: str):
    tokenbank = await get_user_tokenbank(user_id, language)
    if not tokenbank:
        return None
    lowest_token = min(tokenbank.items(), key=lambda x: x[1])
    return lowest_token[0]

async def get_next_exercise_type(user_id: Optional[str], language: str):
    exercise_types = ["matching", "translate", "fill_blank", "audio_transcribe"]
    return random.choice(exercise_types)