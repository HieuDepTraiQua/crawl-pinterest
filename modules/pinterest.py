import asyncio
import random
import requests
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import os
import sys
import json
from database import *
from models.username_entity import UsernameEntity
from models.keyword_entity import KeywordEntity
from models.profile_entity import ProfileEntity
from datetime import datetime


def get_real_avatar_url(avatar_url):
    if not avatar_url:
        return None
    try:
        response = requests.get(avatar_url, timeout=5)
        content_type = response.headers.get("Content-Type", "")

        if "svg" in content_type or "image/svg+xml" in content_type:
            return None

        parsed = urlparse(avatar_url)
        path_parts = parsed.path.split("/")

        if "75x75_RS" in path_parts:
            image_path = "/".join(path_parts[2:])
            original_url = f"https://i.pinimg.com/originals/{image_path}"
            r = requests.get(original_url, timeout=5)
            if r.status_code == 200:
                return original_url
            else:
                return avatar_url
        else:
            return avatar_url

    except Exception as e:
        print(f"⚠️ Lỗi kiểm tra avatar: {e}")
        return None


async def create_browser_context():
    """Tạo và trả về browser và context được cấu hình sẵn"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )
    return p, browser, context


async def crawl_user_profile(list_usernames):
    list_profile = []
    avatar_download_queue = []  # Danh sách các ảnh cần tải

    p, browser, context = await create_browser_context()
    try:
        for username in list_usernames:
            page = await context.new_page()
            try:
                await page.goto(
                    f"https://www.pinterest.com/{username.get('username')}/",
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
                await page.wait_for_function(
                    'document.querySelector("script#__PWS_INITIAL_PROPS__") !== null',
                    timeout=10000,
                )

                # Lấy nội dung JSON nhúng trong thẻ script
                data_script = await page.query_selector("script#__PWS_INITIAL_PROPS__")
                raw_json = await data_script.inner_text()

                # Parse JSON
                data = json.loads(raw_json)

                scroll_distance = random.randint(200, 800)
                sleep_time = random.uniform(1, 3)
                await page.mouse.wheel(0, scroll_distance)
                await asyncio.sleep(sleep_time)

                # Trích xuất thông tin người dùng
                user_resource_key = f'[["field_set_key","unauth_profile"],["is_mobile_fork",true],["username","{username.get("username")}"]]'
                user_data = (
                    data.get("initialReduxState", {})
                    .get("resources", {})
                    .get("UserResource", {})
                    .get(user_resource_key, {})
                    .get("data", {})
                )

                avatar_url = user_data.get("image_xlarge_url", "")
                username_real = user_data.get("username", "")

                final_avatar_url = get_real_avatar_url(avatar_url)
                if final_avatar_url:
                    # Thêm vào hàng đợi tải ảnh
                    avatar_download_queue.append(
                        {
                            "url": final_avatar_url,
                            "username": username_real or username.get("username"),
                        }
                    )

                # Lấy các thông tin cần thiết
                user_info = ProfileEntity(
                    id_profile=user_data.get("id", ""),
                    username=username_real,
                    avatar_url=final_avatar_url,  # Tạm thời lưu URL gốc
                    bio=user_data.get("about", ""),
                    full_name=user_data.get("full_name", ""),
                    following=user_data.get("following_count", ""),
                    follower=user_data.get("follower_count", ""),
                    link=f"https://www.pinterest.com/{username.get('username')}/",
                )
                list_profile.append(user_info)
                print(f"✅ Đã crawl xong profile: {username.get('username')}")
            except Exception as e:
                print(f"❌ Lỗi khi crawl profile {username.get('username')}: {e}")
                continue
            finally:
                await page.close()

        # Lưu danh sách profile vào database
        if list_profile:
            # Tải ảnh sau khi đã crawl xong tất cả
            print("\n🔄 Bắt đầu tải ảnh avatar...")
            for item in avatar_download_queue:
                try:
                    relative_path = download_avatar(item["url"], item["username"])
                    if relative_path:
                        # Cập nhật avatar_url trong list_profile
                        for profile in list_profile:
                            if profile.username == item["username"]:
                                profile.avatar_url = relative_path
                                break
                except Exception as e:
                    print(f"❌ Lỗi khi tải ảnh cho {item['username']}: {e}")

            profile_collection.insert_many(
                [entity.to_dict() for entity in list_profile]
            )
            print(
                f"✅ Đã lưu {len(list_profile)} profile vào MongoDB: {config.DATABASE_NAME}"
            )

            # Cập nhật trạng thái isCrawl cho các username đã crawl
            usernames_to_update = [profile.username for profile in list_profile]
            usernames_collection.update_many(
                {"username": {"$in": usernames_to_update}}, {"$set": {"isCrawl": True}}
            )
            print(
                f"✅ Đã cập nhật trạng thái crawl cho {len(usernames_to_update)} username"
            )

            # Tách fullname và kiểm tra các từ trong collection usernames
            new_keywords = set()
            for profile in list_profile:
                if profile.full_name:
                    # Tách fullname thành các từ riêng lẻ
                    name_parts = profile.full_name.split()

                    for name_part in name_parts:
                        # Kiểm tra xem từ này đã tồn tại trong collection usernames chưa
                        existing_keyword = keywords_collection.find_one(
                            {"keyword": name_part.lower()}
                        )
                        if not existing_keyword:
                            new_keywords.add(name_part.lower())
            
            # Chuyển set thành list các KeywordEntity
            keyword_entities = [
                KeywordEntity(
                    keyword=keyword,
                    isCrawl=False,
                    crawlDate=None,
                )
                for keyword in new_keywords
            ]
            
            # Lưu các username mới vào database
            if keyword_entities:
                keywords_collection.insert_many(
                    [entity.to_dict() for entity in keyword_entities]
                )
                print(
                    f"✅ Đã lưu thêm {len(keyword_entities)} keyword mới"
                )
    finally:
        await browser.close()
        await p.stop()


async def crawl_usernames(keyword: str):
    p, browser, context = await create_browser_context()

    try:
        page = await context.new_page()
        print(f"\n🔍 Tìm người dùng theo từ khóa: {keyword}")
        usernames_data = set()
        search_url = (
            f"https://www.pinterest.com/search/users/?q={keyword.replace(' ', '%20')}"
        )
        await page.goto(search_url)
        await asyncio.sleep(3)

        # Với giới hạn là 20 lần call API và random scroll thì value mặc định là 75
        scroll_times: int = 75
        for i in range(scroll_times):
            print(f"🔄 Cuộn {i+1}/{scroll_times} keyword {keyword}...")
            await page.mouse.wheel(0, random.randint(800, 1200))
            await asyncio.sleep(random.uniform(1.5, 2.5))

        elements = await page.query_selector_all('[data-test-id="user-rep"] a[href]')
        for el in elements:
            href = await el.get_attribute("href")
            if href and href.startswith("/") and len(href.strip("/").split("/")) == 1:
                username = href.strip("/")
                usernames_data.add(username)

        # Kiểm tra username đã tồn tại trong database
        existing_usernames = set(usernames_collection.distinct("username"))
        new_usernames = usernames_data - existing_usernames

        # Convert to UsernameEntity and save to database
        username_entities = [
            UsernameEntity(username=username, isCrawl=False)
            for username in new_usernames
        ]
        if username_entities:
            usernames_collection.insert_many(
                [entity.to_dict() for entity in username_entities]
            )
            print(
                f"✅ Đã lưu {len(username_entities)} username mới với keyword {keyword} vào MongoDB: {config.DATABASE_NAME}"
            )
            if len(usernames_data) > len(new_usernames):
                print(
                    f"ℹ️ Có {len(usernames_data) - len(new_usernames)} username đã tồn tại trong database"
                )

            # Cập nhật trạng thái keyword sau khi lưu xong username
            keywords_collection.update_one(
                {"keyword": keyword},
                {"$set": {"isCrawl": True, "crawlDate": datetime.now()}},
            )
            print(f"✅ Đã cập nhật trạng thái crawl cho keyword: {keyword}")
    finally:
        await browser.close()
        await p.stop()


def download_avatar(image_url, username):
    try:
        current_date = datetime.now().strftime("%d-%m-%Y")
        folder_path = os.path.join("avatars", current_date)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        filename = os.path.join(folder_path, f"{username}.jpg")
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"🖼️ Ảnh avatar đã lưu: {filename}")
            return filename
    except Exception as e:
        print(f"❌ Lỗi tải avatar cho {username}: {e}")