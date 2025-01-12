from typing import Optional
from models import Exercise, TranslateExercise, MatchingExercise, FillBlankExercise, AudioTranscribeExercise
from recommendation import get_next_exercise_type

async def generate_exercise(language: str, token: Optional[str] = None) -> Exercise:
    """
    Simulate exercise generation. In reality, this would call an AI model.
    Returns a predefined exercise for demonstration.
    """
    # Get recommended exercise type for this user and language
    exercise_type = await get_next_exercise_type(None if token is None else token, language)
    
    if exercise_type == "translate":
        data = TranslateExercise(
            input_language=language,
            output_language="english",
            input_sentence="我昨天在那間店裡看到一件新衣服",
            output_sentences=[
                "yesterday at the store I saw a new shirt",
                "I saw a new shirt yesterday at the store",
                "I saw a new shirt at the store yesterday"
            ],
            chunk_options=[
                "yesterday", "at", "I", "of", "saw", "a new shirt",
                "the store", "colorful", "wrong", "other stuff", "mouse", "nope"
            ]
        )
    elif exercise_type == "matching":
        data = MatchingExercise(
            pairs={
                "你好": "hello",
                "再見": "goodbye",
                "謝謝": "thank you",
                "早安": "good morning"
            }
        )
    elif exercise_type == "audio_transcribe":
        data = AudioTranscribeExercise(
            input_language=language,
            audio_url="https://example.com/fake-audio.mp3",  # This would be a real audio URL in production
            chunk_options=[
                "我", "你", "他", "是", "不是", "要",
                "去", "商店", "學校", "吃飯", "喝水"
            ],
            correct_sentences=[
                "我要去商店",
                "我想去商店"
            ]
        )
    else:  # fill_blank
        data = FillBlankExercise(
            input_language=language,
            input_sentence="我 {} 去商店",
            correct_fills=["要", "想", "會"]
        )
    
    return Exercise(type=exercise_type, language=language, data=data)