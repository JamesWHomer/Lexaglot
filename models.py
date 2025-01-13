from pydantic import BaseModel
from typing import Dict, List, Union, Optional, Any
from datetime import datetime

class MatchingExercise(BaseModel):
    pairs: Dict[str, str]
    model_config = {"extra": "allow"}

class TranslateExercise(BaseModel):
    input_language: str
    output_language: str
    input_sentence: str
    output_sentences: List[str]
    chunk_options: List[str]
    model_config = {"extra": "allow"}

class FillBlankExercise(BaseModel):
    input_language: str
    input_sentence: str # Will be something like "Han {} james"
    correct_fills: List[str]
    model_config = {"extra": "allow"}

class AudioTranscribeExercise(BaseModel):
    input_language: str
    audio_url: str
    chunk_options: List[str]
    correct_sentences: List[str]
    model_config = {"extra": "allow"}

class Exercise(BaseModel):
    type: str
    language: str # The language the user is learning
    data: Union[MatchingExercise, TranslateExercise, FillBlankExercise, AudioTranscribeExercise]
    model_config = {"extra": "allow"}

class AttemptDetail(BaseModel):
    timestamp: datetime
    time_spent_ms: int
    response: Any  # The actual response they gave
    model_config = {"extra": "allow"}

class ExerciseAttempt(BaseModel):
    user_id: str
    exercise_id: str
    language: str
    started_at: datetime  # When they first started the exercise
    completed_at: datetime  # When they either completed or skipped
    was_completed: bool  # True if completed, False if skipped
    total_time_spent_ms: int  # Total time across all attempts
    attempt_history: List[AttemptDetail]  # All attempts made before completion/skip
    model_config = {"extra": "allow"}
