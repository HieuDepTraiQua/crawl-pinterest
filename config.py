import os
import sys
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Đọc các biến
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# Project root path
# ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

# # Add project root to Python path
# if ROOT_PATH not in sys.path:
#     sys.path.append(ROOT_PATH)