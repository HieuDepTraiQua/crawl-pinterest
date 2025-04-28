import asyncio
import threading
from queue import Queue
from database import *
from modules.pinterest import crawl_usernames
from modules.pinterest import crawl_user_profile
from modules.keyword_manager import create_keywords
from models.keyword_entity import KeywordEntity
from datetime import datetime

class KeywordQueue:
    def __init__(self):
        self.queue = Queue()
        self.lock = threading.Lock()
        self._load_keywords()

    def _load_keywords(self):
        """Load keywords từ database vào queue"""
        # Kiểm tra số lượng keywords cần crawl
        count = keywords_collection.count_documents({"isCrawl": False})
        if count == 0:
            print("⚠️ Không tìm thấy keywords nào cần crawl")
            return False

        keywords = keywords_collection.find({"isCrawl": False})
        for keyword in keywords:
            self.queue.put(keyword.get("keyword"))
        print(f"✅ Đã load {self.queue.qsize()} keywords vào queue")
        return True

    def get_keyword(self):
        """Lấy keyword từ queue và đánh dấu đã crawl"""
        with self.lock:
            if self.queue.empty():
                return None
            
            keyword = self.queue.get()
            # Đánh dấu keyword đã được crawl
            keywords_collection.update_one(
                {"keyword": keyword},
                {"$set": {"isCrawl": True, "crawlDate": datetime.now()}}
            )
            return keyword

async def worker(queue: KeywordQueue, worker_id: int):
    """Worker function để xử lý crawl"""
    print(f"🔄 Worker {worker_id} đã bắt đầu")
    
    while True:
        keyword = queue.get_keyword()
        if keyword is None:
            print(f"✅ Worker {worker_id} đã hoàn thành")
            break
            
        print(f"📝 Worker {worker_id} đang crawl keyword: {keyword}")
        await crawl_usernames(keyword)

async def main_crawl_username():
    # Tạo queue và load keywords
    queue = KeywordQueue()
    
    # Tạo và chạy 2 worker
    workers = [
        worker(queue, i) for i in range(2)
    ]
    
    # Chạy tất cả workers đồng thời
    await asyncio.gather(*workers)

if __name__ == "__main__":
    # asyncio.run(main_crawl_username()) 
    asyncio.run(crawl_user_profile()) 
    # create_keywords()