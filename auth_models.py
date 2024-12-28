from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    model_config = {"extra": "allow"}

class TokenData(BaseModel):
    username: Optional[str] = None
    token_type: Optional[str] = None  # To distinguish between access and refresh tokens
    model_config = {"extra": "allow"}

class RefreshToken(BaseModel):
    user_id: str
    token: str
    expires_at: datetime
    blacklisted: bool = False
    model_config = {"extra": "allow"}

class User(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    model_config = {
        "extra": "allow",
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "username": "johndoe",
                    "email": "johndoe@example.com",
                    "full_name": "John Doe"
                }
            ]
        }
    }

class UserInDB(User):
    hashed_password: str 