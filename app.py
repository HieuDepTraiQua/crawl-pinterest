import asyncio
import threading
from queue import Queue
from typing import List, Optional
import logging
import sys

from database import *
from modules.pinterest import PinterestCrawler
from modules.keyword_manager import *
from models.keyword_entity import KeywordEntity
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class BaseQueue:
    """Lớp cơ sở cho các queue"""
    def __init__(self):
        self.queue = Queue()
        self.lock = threading.Lock()

    def is_empty(self) -> bool:
        """Kiểm tra queue có rỗng không"""
        with self.lock:
            return self.queue.empty()

    def get(self):
        """Lấy một phần tử từ queue"""
        with self.lock:
            if self.queue.empty():
                return None
            return self.queue.get()


class KeywordQueue(BaseQueue):
    """Queue quản lý các keyword cần crawl"""
    def __init__(self):
        super().__init__()
        self._load_keywords()

    def _load_keywords(self) -> bool:
        """Load keywords từ database vào queue"""
        count = keywords_collection.count_documents({"isCrawl": False})
        if count == 0:
            logger.warning("Không tìm thấy keywords nào cần crawl")
            return False

        keywords = keywords_collection.find({"isCrawl": False})
        for keyword in keywords:
            self.queue.put(keyword.get("keyword"))
        logger.info(f"Đã load {self.queue.qsize()} keywords vào queue")
        return True


class UsernameQueue(BaseQueue):
    """Queue quản lý các username cần crawl"""
    def __init__(self, batch_size: int = 5):
        super().__init__()
        self.batch_size = batch_size
        self._load_usernames()

    def _load_usernames(self) -> bool:
        """Load usernames từ database vào queue theo batch"""
        count = usernames_collection.count_documents({"isCrawl": False})
        if count == 0:
            logger.warning("Không tìm thấy usernames nào cần crawl")
            return False

        usernames = list(usernames_collection.find({"isCrawl": False}))
        for i in range(0, len(usernames), self.batch_size):
            batch = usernames[i : i + self.batch_size]
            self.queue.put(batch)

        logger.info(f"Đã load {self.queue.qsize()} batches usernames vào queue")
        return True


class CrawlerWorker:
    """Lớp cơ sở cho các worker"""
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.crawler = PinterestCrawler()

    async def start(self):
        """Bắt đầu worker"""
        logger.info(f"Worker {self.worker_id} đã bắt đầu")


class KeywordWorker(CrawlerWorker):
    """Worker xử lý crawl username từ keyword"""
    async def process(self, queue: KeywordQueue):
        """Xử lý crawl username từ keyword"""
        while True:
            keyword = queue.get()
            if keyword is None:
                logger.info(f"Worker {self.worker_id} đã hoàn thành")
                break

            logger.info(f"Worker {self.worker_id} đang crawl keyword: {keyword}")
            await self.crawler.crawl_usernames(keyword)


class ProfileWorker(CrawlerWorker):
    """Worker xử lý crawl profile từ username"""
    async def process(self, queue: UsernameQueue):
        """Xử lý crawl profile từ username"""
        while True:
            batch = queue.get()
            if batch is None:
                logger.info(f"Worker {self.worker_id} đã hoàn thành")
                break

            logger.info(f"Worker {self.worker_id} đang crawl batch với {len(batch)} usernames")
            await self.crawler.crawl_user_profile(batch)


class CrawlerManager:
    """Quản lý việc crawl dữ liệu"""
    @staticmethod
    async def crawl_usernames(num_workers: int = 1):
        """Chạy crawl username với số lượng worker cho trước"""
        queue = KeywordQueue()
        workers = [KeywordWorker(i) for i in range(num_workers)]
        await asyncio.gather(*[worker.process(queue) for worker in workers])

    @staticmethod
    async def crawl_profiles(num_workers: int = 1, batch_size: int = 50):
        """Chạy crawl profile với số lượng worker và batch size cho trước"""
        queue = UsernameQueue(batch_size)
        workers = [ProfileWorker(i) for i in range(num_workers)]
        await asyncio.gather(*[worker.process(queue) for worker in workers])


def print_usage():
    """Hiển thị hướng dẫn sử dụng"""
    print("⚠️ Vui lòng chọn chế độ crawl:")
    print("   python app.py crawl_usernames [num_workers]")
    print("   python app.py crawl_profiles [num_workers] [batch_size]")
    print("   python app.py create_keywords")
    print("   python app.py count_keywords")


def main():
    """Hàm chính của chương trình"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "crawl_usernames":
            num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            asyncio.run(CrawlerManager.crawl_usernames(num_workers))
        elif command == "crawl_profiles":
            num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            asyncio.run(CrawlerManager.crawl_profiles(num_workers, batch_size))
        elif command == "create_keywords":
            create_keywords()
        elif command == "count_keywords":
            count_keyword_not_crawl()
        else:
            print("⚠️ Lệnh không hợp lệ!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Lỗi khi thực thi lệnh: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
