from pydantic import BaseModel
from typing import Dict, List, Union, Optional, Any
from datetime import datetime

class MatchingExercise(BaseModel):
    data: Dict[str, str]
    model_config = {"extra": "allow"}

class TranslateExercise(BaseModel):
    input_language: str
    output_language: str
    input_sentence: str
    output_sentences: List[str]
    chunk_options: List[str]
    model_config = {"extra": "allow"}

class Exercise(BaseModel):
    type: str
    data: Union[MatchingExercise, TranslateExercise]
    model_config = {"extra": "allow"}

class ExerciseAttempt(BaseModel):
    user_id: str
    exercise_id: str
    language: str
    completed_at: datetime
    time_spent_ms: int  # How long the exercise took in milliseconds
    user_response: Any  # Store whatever response format the app sends
    model_config = {"extra": "allow"}
