# import requests

# exercise_data = {
#     "type": "matching",
#     "data": {
#         "pairs": {
#             "guest": "gäst",
#             "airplane": "flygplan",
#             "guide": "guide",
#             "suitcase": "resväska",
#             "Iceland": "island"
#         }
#     }
# }

# exercise_data = {
#     "type": "translate",
#     "data": {
#         "input_language": "chinese",
#         "output_language": "english",
#         "input_sentence": "我昨天在那間店裡看到一件新衣服",
#         "output_sentences": [
#             'yesterday at the store I saw a new shirt',
#             'I saw a new shirt yesterday at the store',
#             'I saw a new shirt at the store yesterday',
#         ],
#         "chunk_options": [
#             'yesterday',
#             'at',
#             'I',
#             'of',
#             'saw',
#             'a new shirt',
#             'the store',
#             'colorful',
#             'wrong',
#             'other stuff',
#             'mouse',
#             'nope',
#         ]
#     }
# }

# response = requests.post("http://172.24.105.161:8000/exercise", json=exercise_data)
# print(response.json())

# # To get the exercise, use the _id from the response    
# exercise_id = response.json()["_id"]
# get_response = requests.get(f"http://127.0.0.1:8000/exercise/{exercise_id}")
# print(get_response.json())

# print("Data:", get_response.json()["data"])

import asyncio
from database import get_user_tokenbank, set_user_tokenbank, update_token_count

async def test_tokenbank():
    # Set entire tokenbank
    tokens = {"cat": 69, "dog": 100, "bird": 42}
    await set_user_tokenbank("james", "es", tokens) # Shouldn't use username as ID
    
    # Get entire tokenbank
    result = await get_user_tokenbank("james", "es")
    print("All tokens:", result)
    
    # Update single token
    await update_token_count("james", "es", "cat", 75)

# Run the test
asyncio.run(test_tokenbank())