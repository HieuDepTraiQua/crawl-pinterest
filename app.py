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
            return keyword

class UsernameQueue:
    def __init__(self, batch_size=5):
        self.queue = Queue()
        self.lock = threading.Lock()
        self.batch_size = batch_size
        self._load_usernames()

    def _load_usernames(self):
        """Load usernames từ database vào queue theo batch"""
        # Kiểm tra số lượng usernames cần crawl
        count = usernames_collection.count_documents({"isCrawl": False})
        if count == 0:
            print("⚠️ Không tìm thấy usernames nào cần crawl")
            return False

        usernames = list(usernames_collection.find({"isCrawl": False}))
        # Chia usernames thành các batch
        for i in range(0, len(usernames), self.batch_size):
            batch = usernames[i:i + self.batch_size]
            self.queue.put(batch)
        
        print(f"✅ Đã load {self.queue.qsize()} batches usernames vào queue")
        return True

    def get_batch(self):
        """Lấy một batch usernames từ queue"""
        with self.lock:
            if self.queue.empty():
                return None
            return self.queue.get()

async def keyword_worker(queue: KeywordQueue, worker_id: int):
    """Worker function để xử lý crawl username"""
    print(f"🔄 Worker {worker_id} đã bắt đầu")
    
    while True:
        keyword = queue.get_keyword()
        if keyword is None:
            print(f"✅ Worker {worker_id} đã hoàn thành")
            break
            
        print(f"📝 Worker {worker_id} đang crawl keyword: {keyword}")
        await crawl_usernames(keyword)

async def profile_worker(queue: UsernameQueue, worker_id: int):
    """Worker function để xử lý crawl profile"""
    print(f"🔄 Worker {worker_id} đã bắt đầu")
    
    while True:
        batch = queue.get_batch()
        if batch is None:
            print(f"✅ Worker {worker_id} đã hoàn thành")
            break
            
        print(f"📝 Worker {worker_id} đang crawl batch với {len(batch)} usernames")
        await crawl_user_profile(batch)

async def main_crawl_username(num_workers=1):
    """Chạy crawl username với số lượng worker cho trước"""
    # Tạo queue và load keywords
    queue = KeywordQueue()
    
    # Tạo và chạy workers
    workers = [
        keyword_worker(queue, i) for i in range(num_workers)
    ]
    
    # Chạy tất cả workers đồng thời
    await asyncio.gather(*workers)

async def main_crawl_profile(num_workers=1, batch_size=50):
    """Chạy crawl profile với số lượng worker và batch size cho trước"""
    # Tạo queue và load usernames
    queue = UsernameQueue(batch_size)
    
    # Tạo và chạy workers
    workers = [
        profile_worker(queue, i) for i in range(num_workers)
    ]
    
    # Chạy tất cả workers đồng thời
    await asyncio.gather(*workers)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("⚠️ Vui lòng chọn chế độ crawl:")
        print("   python app.py crawl_username [num_workers]")
        print("   python app.py crawl_profile [num_workers] [batch_size]")
        print("   python app.py create_keywords")
        sys.exit(1)

    command = sys.argv[1]
    
    if command == "crawl_username":
        num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        asyncio.run(main_crawl_username(num_workers))
    elif command == "crawl_profile":
        num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        asyncio.run(main_crawl_profile(num_workers, batch_size))
    elif command == "create_keywords":
        create_keywords()
    else:
        print("⚠️ Lệnh không hợp lệ!")
        sys.exit(1)