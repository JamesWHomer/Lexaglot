import requests

exercise_data = {
    "type": "matching",
    "data": {
        "guest": "gäst",
        "airplane": "flygplan",
        "guide": "guide",
        "suitcase": "resväska",
        "Iceland": "island"
    }
}

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

response = requests.post("http://172.24.105.161:8000/exercise", json=exercise_data)
print(response.json())

# # To get the exercise, use the _id from the response    
# exercise_id = response.json()["_id"]
# get_response = requests.get(f"http://127.0.0.1:8000/exercise/{exercise_id}")
# print(get_response.json())

# print("Data:", get_response.json()["data"])