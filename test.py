import asyncio
import random
import csv
import sys
import requests
from urllib.parse import urlparse, unquote, parse_qs
import json as pyjson
from playwright.async_api import async_playwright

def get_real_avatar_url(avatar_url):
    if not avatar_url:
        return None

    try:
        response = requests.get(avatar_url, timeout=5)
        content_type = response.headers.get("Content-Type", "")

        if "svg" in content_type or "image/svg+xml" in content_type:
            return None  # ảnh mặc định dạng chữ cái

        parsed = urlparse(avatar_url)
        path_parts = parsed.path.split('/')

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
        print(f"\u26a0\ufe0f Lỗi kiểm tra avatar: {e}")
        return None


async def fetch_user_data(context, username):
    user_data = {}

    async def handle_response(response):
        nonlocal user_data
        print(response.url)
        if "UserResource" in response.url:
            try:
                json_data = await response.json()
                data = json_data.get("resource_response", {}).get("data", {})
                if data.get("username") == username and not user_data:
                    user_data.update(data)
                    print(f"✅ Bắt được dữ liệu user từ: {response.url}")
            except Exception as e:
                print(f"❌ Lỗi khi parse response cho {username}: {e}")

    context.on("response", handle_response)

    page = await context.new_page()
    await page.goto(f"https://www.pinterest.com/{username}/", wait_until="networkidle")
    await asyncio.sleep(6)
    await page.close()

    raw_avatar = user_data.get("image_medium_url")
    avatar_url = get_real_avatar_url(raw_avatar)

    return {
        "username": username,
        "full_name": user_data.get("full_name"),
        "bio": user_data.get("about"),
        "avatar_url": avatar_url or ""
    }


async def scrape_usernames(page, keyword: str, scroll_times: int = 15):
    usernames = set()
    search_url = f"https://www.pinterest.com/search/users/?q={keyword.replace(' ', '%20')}"
    await page.goto(search_url)
    await asyncio.sleep(3)

    for i in range(scroll_times):
        print(f"🔄 Cuộn {i+1}/{scroll_times}...")
        await page.mouse.wheel(0, random.randint(800, 1200))
        await asyncio.sleep(random.uniform(1.5, 2.5))

    elements = await page.query_selector_all('[data-test-id="user-rep"] a[href]')
    for el in elements:
        href = await el.get_attribute("href")
        if href and href.startswith("/") and len(href.strip("/").split("/")) == 1:
            username = href.strip("/")
            usernames.add(username)

    print(f"✅ Tìm được {len(usernames)} username.")
    return list(usernames)


async def run_pipeline(keyword: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )
        page = await context.new_page()

        print(f"\n🔍 Tìm người dùng theo từ khóa: {keyword}")
        # usernames = await scrape_usernames(page, keyword)
        usernames = ["designpoolpatterns"]
        profile_data = []

        for i, username in enumerate(usernames):
            print(f"📄 [{i+1}/{len(usernames)}] Đang lấy thông tin: {username}")
            try:
                info = await fetch_user_data(context, username)
                if info["full_name"] or info["bio"] or info["avatar_url"]:
                    profile_data.append(info)
                else:
                    print(f"⚠️ Không tìm thấy info: {username}")
            except Exception as e:
                print(f"❌ Lỗi {username}: {e}")

        await browser.close()

        output_file = f"profiles_{keyword.replace(' ', '_')}.csv"
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["username", "full_name", "bio", "avatar_url"])
            writer.writeheader()
            for row in profile_data:
                writer.writerow(row)

        print(f"\n✅ Hoàn tất. Đã lưu {len(profile_data)} hồ sơ vào: {output_file}")


if __name__ == "__main__":
    # if len(sys.argv) < 2:
    #     print("⚠️ Vui lòng nhập từ khóa tìm kiếm. VD:")
    #     print("   python pinterest_scraper.py \"interior design\"")
    #     sys.exit(1)

    # keyword = " ".join(sys.argv[1:])
    # asyncio.run(run_pipeline(keyword))
    asyncio.run(run_pipeline("trung hieu"))
