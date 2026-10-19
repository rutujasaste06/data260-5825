from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
db = client["s5825_doc"]
messages = db["messages"]
summaries = db["summaries"]
episodes = db["episodes"]
messages.create_index([("user_id", 1), ("session_id", 1), ("created_at", 1)])