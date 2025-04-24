import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Đọc các biến
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")