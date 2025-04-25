import string
from database import *
from models.keyword_entity import KeywordEntity

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
        print(
            f"✅ Đã lưu {len(keyword_entities)} keywords vào MongoDB: {config.DATABASE_NAME}"
        )


if __name__ == "__main__":
    create_keywords()
