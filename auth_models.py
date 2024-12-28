from pydantic import BaseModel, Field
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    model_config = {"extra": "allow"}

class TokenData(BaseModel):
    username: Optional[str] = None
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