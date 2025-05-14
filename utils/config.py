from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

class Config:
    """Lớp quản lý cấu hình cho toàn bộ project"""
    
    # Cấu hình database
    DATABASE_NAME = os.getenv("DATABASE_NAME")
    MONGO_URL = os.getenv("MONGO_URL")
    CRAWL_CONTROLLER_ENDPOINT = os.getenv("CRAWL_CONTROLLER_ENDPOINT")
    
    # Cấu hình crawler
    CRAWLER_CONFIG: Dict[str, Any] = {
        "default_workers": 1,
        "default_batch_size": 50,
        "max_retries": 3,
        "timeout": 60,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "viewport": {"width": 1280, "height": 800},
        "locale": "en-US"
    }
    
    # Cấu hình thư mục
    DIRECTORIES: Dict[str, str] = {
        "avatars": "avatars"
    }
    
    # RabbitMQ Configuration
    RABBITMQ_CONFIG = {
        "host": "localhost",
        "port": 5672,
        "username": "guest",
        "password": "guest",
        "queue_name": "pinterest.crawler.queue"
    }
    
    @classmethod
    def create_directories(cls) -> None:
        """Tạo các thư mục cần thiết nếu chưa tồn tại"""
        for directory in cls.DIRECTORIES.values():
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    @classmethod
    def get_avatar_path(cls, username: str) -> str:
        """Lấy đường dẫn lưu avatar cho username
        
        Args:
            username (str): Tên người dùng
            
        Returns:
            str: Đường dẫn đầy đủ để lưu avatar
        """
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        folder_path = os.path.join(cls.DIRECTORIES["avatars"], current_date)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return os.path.join(folder_path, f"{username}.jpg") 