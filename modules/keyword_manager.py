from utils.config import Config
import string
from database import *
from models.keyword_entity import KeywordEntity
from utils.logger import setup_logger
import requests

logger = setup_logger(__name__)


# Hàm tạo default keyword serach
def create_keywords():
    """Tạo và lưu các keywords vào database"""
    # Tạo danh sách các ký tự từ a-z và số 0-9
    keywords = list(string.ascii_lowercase + string.digits)

    # Chuyển đổi thành KeywordEntity
    keyword_entities = [
        KeywordEntity(keyword=keyword, isCrawl=False, crawlDate=None)
        for keyword in keywords
    ]

    # Lưu vào database
    if keyword_entities:
        keywords_collection.insert_many(
            [entity.to_dict() for entity in keyword_entities]
        )
        logger.info(
            f"✅ Đã lưu {len(keyword_entities)} keywords vào MongoDB: {Config.DATABASE_NAME}"
        )


def count_keyword_not_crawl():
    count = keywords_collection.count_documents({"isCrawl": False})
    logger.info(f"✅ Số lượng keyword chưa crawl: {count}")

import json

# def test():
#     file_path = "F:/Hieu/HieuHocCode/Data_Scraping/crawl-printerset/avatars/29-04-2025/abubblylife.jpg"
    
#     with open(file_path, "rb") as file:
#         files = {
#             "files": ("abubblylife.jpg", file, "image/jpeg")
#         }

#         raw_data = {
#             "id_profile": "12596211366232262",
#             "username": "abubblylife",
#             "avatar_url": "avatars/29-04-2025/abubblylife.jpg",
#             "bio": "DIYer, party crafter, fashion obsessed, foodie, red wine & bubbly lover, blogger at A Bubbly Life. Mom to 3 precious littles.",
#             "full_name": "A Bubbly Life",
#             "following": 294,
#             "follower": 30365,
#             "link": "https://www.pinterest.com/Abubblylife/",
#         }
        
#         json_data = json.dumps(raw_data)

#         url = "http://localhost:8080/api/upload/multiple"
        
#         try:
#             response = requests.post(url, files=files, data={'data': json_data})

#             if response.status_code == 200:
#                 print("Dữ liệu đã được gửi thành công:", response.json())
#             else:
#                 print("Yêu cầu thất bại với mã lỗi:", response.status_code)
#                 print(response.text)
#         except requests.exceptions.RequestException as e:
#             print("Có lỗi xảy ra trong khi gửi request:", e)