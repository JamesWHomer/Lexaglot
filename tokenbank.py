from typing import Dict
from db import tokenbank_collection

async def get_user_tokenbank(user_id: str, language: str) -> Dict[str, int]:
    """
    Retrieve the tokenbank for a specific user and language
    """
    result = await tokenbank_collection.find_one({"user_id": user_id, "language": language})
    if result:
        return result.get("tokens", {})
    return {} 

async def set_user_tokenbank(user_id: str, language: str, tokens: Dict[str, int]) -> bool:
    """
    Set or update the tokenbank for a specific user and language
    """
    result = await tokenbank_collection.update_one(
        {"user_id": user_id, "language": language},
        {"$set": {"tokens": tokens}},
        upsert=True
    )
    return result.acknowledged 

async def update_token_value(user_id: str, language: str, token: str, value: int) -> bool:
    """
    Update or set the count for a specific token in user's tokenbank
    """
    result = await tokenbank_collection.update_one(
        {"user_id": user_id, "language": language},
        {"$set": {f"tokens.{token}": value}},
        upsert=True
    )
    return result.acknowledged 