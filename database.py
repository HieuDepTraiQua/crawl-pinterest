from utils.config import Config
from pymongo import MongoClient

client = MongoClient(Config.MONGO_URL)
db = client[Config.DATABASE_NAME]

print(f"✅ Kết nối đến MongoDB: {Config.DATABASE_NAME}")

profile_collection = db["profiles"]
usernames_collection = db["usernames"]
keywords_collection = db["keywords"]