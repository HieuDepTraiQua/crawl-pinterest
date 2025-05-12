import asyncio
import threading
from queue import Queue
from typing import List, Optional
import sys
import psutil
import math

from database import *
from modules.pinterest import PinterestCrawler
from modules.keyword_manager import *
from models.keyword_entity import KeywordEntity
from utils.logger import setup_logger
from utils.config import Config
import argparse


# Cấu hình logger
logger = setup_logger(__name__)

# Tạo các thư mục cần thiết
Config.create_directories()

def calculate_optimal_workers() -> int:
    """Tính toán số lượng worker tối ưu dựa trên tài nguyên hệ thống"""
    try:
        # Lấy thông tin CPU và Memory
        cpu_count = psutil.cpu_count(logical=True)
        memory = psutil.virtual_memory()
        
        # Tính toán giới hạn dựa trên 90% tài nguyên
        cpu_limit = math.floor(cpu_count * 0.9)
        memory_limit = math.floor(memory.total * 0.9)
        
        # Ước tính mỗi worker sử dụng khoảng 250MB memory
        memory_based_workers = math.floor(memory_limit / (250 * 1024 * 1024))
        
        # Lấy giá trị nhỏ hơn giữa CPU và Memory
        optimal_workers = min(cpu_limit, memory_based_workers)
        
        # Đảm bảo ít nhất 1 worker
        optimal_workers = max(1, optimal_workers)
        
        logger.info(f"CPU cores: {cpu_count}, Memory: {memory.total / (1024*1024*1024):.2f}GB")
        logger.info(f"Optimal workers calculated: {optimal_workers}")
        
        return optimal_workers
    except Exception as e:
        logger.error(f"Error calculating optimal workers: {e}")
        return 1  # Fallback to 1 worker if calculation fails

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
    def __init__(self, batch_size: int = Config.CRAWLER_CONFIG["default_batch_size"]):
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
    async def crawl_usernames(num_workers: int = Config.CRAWLER_CONFIG["default_workers"]):
        """Chạy crawl username với số lượng worker cho trước"""
        queue = KeywordQueue()
        workers = [KeywordWorker(i) for i in range(num_workers)]
        await asyncio.gather(*[worker.process(queue) for worker in workers])

    @staticmethod
    async def crawl_profiles(num_workers: int = Config.CRAWLER_CONFIG["default_workers"], 
                           batch_size: int = Config.CRAWLER_CONFIG["default_batch_size"]):
        """Chạy crawl profile với số lượng worker và batch size cho trước"""
        queue = UsernameQueue(batch_size)
        workers = [ProfileWorker(i) for i in range(num_workers)]
        await asyncio.gather(*[worker.process(queue) for worker in workers])


def main():
    """Hàm chính của chương trình"""
    
    # Khởi tạo parser để xử lý đối số từ dòng lệnh
    parser = argparse.ArgumentParser(description="Chương trình crawler cho Pinterest")
    
    # Định nghĩa các lệnh có thể có
    parser.add_argument('command', help="Lệnh cần thực thi", choices=['crawl_usernames', 'crawl_profiles', 'create_keywords', 'count_keywords'])
    
    # Thêm các đối số phụ (nếu cần)
    parser.add_argument('num_workers', type=int, nargs='?', default=None, help="Số lượng workers")
    parser.add_argument('batch_size', type=int, nargs='?', default=None, help="Batch size cho crawl_profiles")
    
    # Phân tích các đối số
    args = parser.parse_args()
    
    # Xử lý các lệnh tương ứng
    try:
        if args.command == "crawl_usernames":
            num_workers = args.num_workers if args.num_workers else calculate_optimal_workers()
            asyncio.run(CrawlerManager.crawl_usernames(num_workers))
        elif args.command == "crawl_profiles":
            num_workers = args.num_workers if args.num_workers else calculate_optimal_workers()
            batch_size = args.batch_size if args.batch_size else Config.CRAWLER_CONFIG["default_batch_size"]
            asyncio.run(CrawlerManager.crawl_profiles(num_workers, batch_size))
        elif args.command == "create_keywords":
            create_keywords()
        elif args.command == "count_keywords":
            count_keyword_not_crawl()
    except Exception as e:
        logger.error(f"Lỗi khi thực thi lệnh: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
