import config
from pymongo import MongoClient

client = MongoClient(config.MONGO_URL)
db = client[config.DATABASE_NAME]

print(f"✅ Kết nối đến MongoDB: {config.DATABASE_NAME}")

profile = db["profile"]