import asyncio
import random
import requests
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import os
import json
from typing import List, Set, Optional, Tuple
from datetime import datetime
import paramiko
from io import BytesIO

from database import *
from models.username_entity import UsernameEntity
from models.keyword_entity import KeywordEntity
from models.profile_entity import ProfileEntity
from utils.logger import setup_logger
from utils.config import Config

# Cấu hình logger
logger = setup_logger(__name__)


class PinterestCrawler:
    """Lớp chính để thực hiện các thao tác crawl dữ liệu từ Pinterest"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None

    async def __aenter__(self):
        """Khởi tạo browser và context khi sử dụng with statement"""
        self.playwright, self.browser, self.context = (
            await self._create_browser_context()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Đóng browser và context khi thoát with statement"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    @staticmethod
    async def _create_browser_context() -> Tuple:
        """Tạo và trả về browser và context được cấu hình sẵn"""
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=Config.CRAWLER_CONFIG["user_agent"],
            viewport=Config.CRAWLER_CONFIG["viewport"],
            locale=Config.CRAWLER_CONFIG["locale"],
        )
        return p, browser, context

    @staticmethod
    def _get_real_avatar_url(avatar_url: str) -> Optional[str]:
        """Kiểm tra và lấy URL avatar thực tế"""
        if not avatar_url:
            return None
        try:
            # Bỏ default avatar
            # response = requests.get(
            #     avatar_url, timeout=Config.CRAWLER_CONFIG["timeout"]
            # )
            # content_type = response.headers.get("Content-Type", "")

            # if "svg" in content_type or "image/svg+xml" in content_type:
            #     return None

            parsed = urlparse(avatar_url)
            path_parts = parsed.path.split("/")

            if "75x75_RS" in path_parts:
                image_path = "/".join(path_parts[2:])
                original_url = f"https://i.pinimg.com/originals/{image_path}"
                r = requests.get(original_url, timeout=Config.CRAWLER_CONFIG["timeout"])
                return original_url if r.status_code == 200 else avatar_url
            return avatar_url

        except Exception as e:
            logger.error(f"Lỗi kiểm tra avatar: {e}")
            return None

    @staticmethod
    def _download_avatar(image_url: str, username: str) -> Optional[str]:
        """Tải avatar về local hoặc remote server tùy theo môi trường"""
        try:
            # Lấy đường dẫn gốc
            base_path = Config.get_avatar_path(username)
            base_dir = os.path.dirname(base_path)
            base_filename = os.path.basename(base_path)

            # Kiểm tra môi trường
            is_docker = os.path.exists("/.dockerenv")

            if is_docker:
                # Cấu hình SFTP
                sftp_host = "192.168.161.230"
                sftp_username = os.environ.get("SFTP_USERNAME", "htsc")
                sftp_password = os.environ.get("SFTP_PASSWORD", "Htsc@123")
                remote_base_path = "/mnt/data/pinterest/avatars"

                # Tạo thư mục theo ngày
                today = datetime.now().strftime("%Y-%m-%d")
                remote_dir = f"{remote_base_path}/{today}"

                # Tạo thư mục trên remote server
                def get_next_remote_folder():
                    folder = remote_dir
                    suffix = 1
                    while True:
                        try:
                            with paramiko.SSHClient() as ssh:
                                ssh.set_missing_host_key_policy(
                                    paramiko.AutoAddPolicy()
                                )
                                ssh.connect(
                                    sftp_host,
                                    username=sftp_username,
                                    password=sftp_password,
                                )
                                with ssh.open_sftp() as sftp:
                                    try:
                                        sftp.stat(folder)
                                        # Đếm số file trong thư mục
                                        file_count = len(sftp.listdir(folder))
                                        if file_count < 5000:
                                            return folder
                                    except FileNotFoundError:
                                        sftp.mkdir(folder)
                                        return folder

                                # Tạo thư mục mới với suffix
                                suffix += 1
                                folder = f"{remote_dir}_{suffix}"
                        except Exception as e:
                            logger.error(f"Lỗi khi tạo thư mục remote: {e}")
                            return None

                # Lấy thư mục phù hợp
                target_dir = get_next_remote_folder()
                if not target_dir:
                    return None

                remote_path = f"{target_dir}/{base_filename}"

                # Tải ảnh và upload qua SFTP
                response = requests.get(
                    image_url, timeout=Config.CRAWLER_CONFIG["timeout"]
                )
                if response.status_code == 200:
                    with paramiko.SSHClient() as ssh:
                        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        ssh.connect(
                            sftp_host, username=sftp_username, password=sftp_password
                        )
                        with ssh.open_sftp() as sftp:
                            with BytesIO(response.content) as file_obj:
                                sftp.putfo(file_obj, remote_path)
                    logger.info(f"Ảnh avatar đã lưu remote: {remote_path}")
                    return remote_path
                return None
            else:
                # Xử lý local như cũ
                def get_next_folder():
                    folder = base_dir
                    suffix = 1
                    while True:
                        if not os.path.exists(folder):
                            os.makedirs(folder)
                            return folder

                        file_count = len(
                            [
                                f
                                for f in os.listdir(folder)
                                if os.path.isfile(os.path.join(folder, f))
                            ]
                        )
                        if file_count < 5000:
                            return folder

                        suffix += 1
                        folder = f"{base_dir}_{suffix}"

                target_dir = get_next_folder()
                filename = os.path.join(target_dir, base_filename)

                response = requests.get(
                    image_url, timeout=Config.CRAWLER_CONFIG["timeout"]
                )

                if response.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Ảnh avatar đã lưu local: {filename}")
                    return filename
                return None

        except Exception as e:
            logger.error(f"Lỗi tải avatar cho {username}: {e}")
            return None

    async def _extract_profile_data(
        self, page, username: str
    ) -> Optional[ProfileEntity]:
        """Trích xuất thông tin profile từ trang Pinterest"""
        try:
            await page.goto(
                f"https://www.pinterest.com/{username}/",
                wait_until="domcontentloaded",
                timeout=Config.CRAWLER_CONFIG["timeout"]
                * 1000,  # Chuyển đổi sang milliseconds
            )
            await page.wait_for_function(
                'document.querySelector("script#__PWS_INITIAL_PROPS__") !== null',
                timeout=10000,
            )

            data_script = await page.query_selector("script#__PWS_INITIAL_PROPS__")
            raw_json = await data_script.inner_text()
            data = json.loads(raw_json)

            # Mô phỏng hành vi người dùng
            # scroll_distance = random.randint(200, 800)
            # sleep_time = random.uniform(1, 3)
            # await page.mouse.wheel(0, scroll_distance)
            # await asyncio.sleep(sleep_time)

            user_resource_key = f'[["field_set_key","unauth_profile"],["is_mobile_fork",true],["username","{username}"]]'
            user_data = (
                data.get("initialReduxState", {})
                .get("resources", {})
                .get("UserResource", {})
                .get(user_resource_key, {})
                .get("data", {})
            )

            avatar_url = user_data.get("image_xlarge_url", "")
            username_real = user_data.get("username", "")

            return ProfileEntity(
                id_profile=user_data.get("id", ""),
                username=username_real,
                avatar_url=self._get_real_avatar_url(avatar_url),
                bio=user_data.get("about", ""),
                full_name=user_data.get("full_name", ""),
                following=user_data.get("following_count", ""),
                follower=user_data.get("follower_count", ""),
                link=f"https://www.pinterest.com/{username}/",
            )
        except Exception as e:
            logger.error(f"Lỗi khi crawl profile {username}: {e}")
            return None

    async def crawl_user_profile(self, list_usernames: List[dict]) -> None:
        """Crawl thông tin profile từ danh sách username"""
        async with self:
            list_profile = []
            avatar_download_queue = []

            for username in list_usernames:
                page = await self.context.new_page()
                try:
                    profile = await self._extract_profile_data(
                        page, username.get("username")
                    )
                    if profile:
                        list_profile.append(profile)
                        if profile.avatar_url:
                            avatar_download_queue.append(
                                {
                                    "url": profile.avatar_url,
                                    "username": profile.username
                                    or username.get("username"),
                                }
                            )
                        logger.info(
                            f"Đã crawl xong profile: {username.get('username')}"
                        )
                finally:
                    await page.close()

            if list_profile:
                await self._process_profiles(list_profile, avatar_download_queue)

    async def _process_profiles(
        self, list_profile: List[ProfileEntity], avatar_download_queue: List[dict]
    ) -> None:
        """Xử lý và lưu thông tin profile"""
        # Tải ảnh avatar
        logger.info("Bắt đầu tải ảnh avatar...")
        for item in avatar_download_queue:
            try:
                relative_path = self._download_avatar(item["url"], item["username"])
                if relative_path:
                    for profile in list_profile:
                        if profile.username == item["username"]:
                            profile.avatar_url = relative_path
                            break
            except Exception as e:
                logger.error(f"Lỗi khi tải ảnh cho {item['username']}: {e}")

        # Lưu profile vào database
        profile_collection.insert_many([entity.to_dict() for entity in list_profile])
        logger.info(f"Đã lưu {len(list_profile)} profile vào MongoDB")

        # Cập nhật trạng thái crawl
        usernames_to_update = [profile.username for profile in list_profile]
        usernames_collection.update_many(
            {"username": {"$in": usernames_to_update}}, {"$set": {"isCrawl": True}}
        )
        logger.info(
            f"Đã cập nhật trạng thái crawl cho {len(usernames_to_update)} username"
        )

        # Xử lý và lưu keywords mới
        self._process_keywords(list_profile)

    def is_standard_alpha(self, word: str) -> bool:
        """Chỉ cho phép ký tự chữ và số trong bảng mã Latin cơ bản"""
        return all(c.isalnum() and c.isascii() for c in word)

    def _process_keywords(self, list_profile: List[ProfileEntity]) -> None:
        """Xử lý và lưu keywords từ fullname"""
        new_keywords = set()
        for profile in list_profile:
            if profile.full_name:
                name_parts = profile.full_name.split()
                for name_part in name_parts:
                    keyword = name_part.lower()
                    if not self.is_standard_alpha(keyword):
                        continue  # Bỏ qua từ chứa ký tự đặc biệt hoặc non-standard
                    existing_keyword = keywords_collection.find_one({"keyword": keyword})
                    if not existing_keyword:
                        new_keywords.add(keyword)

        if new_keywords:
            keyword_entities = [
                KeywordEntity(
                    keyword=keyword,
                    isCrawl=False,
                    crawlDate=None,
                )
                for keyword in new_keywords
            ]
            keywords_collection.insert_many(
                [entity.to_dict() for entity in keyword_entities]
            )
            logger.info(f"Đã lưu thêm {len(keyword_entities)} keyword mới")

    async def crawl_usernames(self, keyword: str) -> None:
        """Crawl danh sách username từ keyword"""
        async with self:
            page = await self.context.new_page()
            try:
                logger.info(f"Tìm người dùng theo từ khóa: {keyword}")
                usernames_data = set()
                search_url = f"https://www.pinterest.com/search/users/?q={keyword.replace(' ', '%20')}"
                await page.goto(search_url)
                await asyncio.sleep(3)

                scroll_times = 75
                for i in range(scroll_times):
                    logger.info(f"Cuộn {i+1}/{scroll_times} keyword {keyword}...")
                    await page.mouse.wheel(0, random.randint(800, 1200))
                    await asyncio.sleep(random.uniform(1.5, 2.5))

                elements = await page.query_selector_all(
                    '[data-test-id="user-rep"] a[href]'
                )
                for el in elements:
                    href = await el.get_attribute("href")
                    if (
                        href
                        and href.startswith("/")
                        and len(href.strip("/").split("/")) == 1
                    ):
                        usernames_data.add(href.strip("/"))

                self._save_usernames(usernames_data, keyword)
            finally:
                await page.close()

    def _save_usernames(self, usernames_data: Set[str], keyword: str) -> None:
        """Lưu danh sách username vào database"""
        existing_usernames_cursor = usernames_collection.find(
            {"username": {"$in": list(usernames_data)}}, {"username": 1}
        )
        existing_usernames = set(user["username"] for user in existing_usernames_cursor)
        new_usernames = usernames_data - existing_usernames

        if new_usernames:
            username_entities = [
                UsernameEntity(username=username, isCrawl=False)
                for username in new_usernames
            ]
            usernames_collection.insert_many(
                [entity.to_dict() for entity in username_entities]
            )
            logger.info(
                f"Đã lưu {len(username_entities)} username mới với keyword {keyword}"
            )

            if len(usernames_data) > len(new_usernames):
                logger.info(
                    f"Có {len(usernames_data) - len(new_usernames)} username đã tồn tại trong database"
                )

            keywords_collection.update_one(
                {"keyword": keyword},
                {"$set": {"isCrawl": True, "crawlDate": datetime.now()}},
            )
            logger.info(f"Đã cập nhật trạng thái crawl cho keyword: {keyword}")
