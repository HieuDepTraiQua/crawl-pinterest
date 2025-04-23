import asyncio
import random
import csv
import requests
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import codecs
from datetime import datetime
import os
import sys

def get_real_avatar_url(avatar_url):
    if not avatar_url:
        return None
    try:
        response = requests.get(avatar_url, timeout=5)
        content_type = response.headers.get("Content-Type", "")

        if "svg" in content_type or "image/svg+xml" in content_type:
            return None

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
        print(f"⚠️ Lỗi kiểm tra avatar: {e}")
        return None


async def fetch_user_data(context, username):
    page = await context.new_page()
    await page.goto(f"https://www.pinterest.com/{username}/", wait_until="domcontentloaded", timeout=60000)
    # await page.goto(f"https://www.pinterest.com/{username}/", wait_until="networkidle")
    await page.wait_for_selector('[data-test-id="profile-header"]', timeout=10000)

     # 👉 Mô phỏng thao tác người dùng
    scroll_distance = random.randint(200, 800)
    sleep_time = random.uniform(2, 5)
    await page.mouse.wheel(0, scroll_distance)
    await asyncio.sleep(sleep_time)
    
    async def safe_text(el):
        return await el.inner_text() if el else ""

    async def safe_attr(el, attr):
        return await el.get_attribute(attr) if el else ""

    avatar_el = await page.query_selector('[data-test-id="gestalt-avatar-svg"] img')
    name_el = await page.query_selector('[data-test-id="profile-name"] div')
    username_el = await page.query_selector('span.JlN.zDA')
    bio_el = await page.query_selector('[data-test-id="profileAboutText"] span')
    if not bio_el:
        bio_el = await page.query_selector('[aria-label="Expand about section"] span')

    avatar_url = await safe_attr(avatar_el, "src")
    full_name = await safe_text(name_el)
    username_real = await safe_text(username_el)
    bio = await safe_text(bio_el)
    
    await page.close()
    
    final_avatar_url = get_real_avatar_url(avatar_url)
    if final_avatar_url:
        download_avatar(final_avatar_url, username_real or username)

    return {
        "username": username_real or username,
        "full_name": full_name,
        "bio": bio,
        "avatar_url": final_avatar_url,
        "link": f"https://www.pinterest.com/{username}/"   
    }


async def scrape_usernames(page, keyword: str, scroll_times: int = 30):
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
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )
        page = await context.new_page()

        print(f"\n🔍 Tìm người dùng theo từ khóa: {keyword}")
        usernames = await scrape_usernames(page, keyword)
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = f"profiles_{keyword.replace(' ', '_')}_{timestamp}.csv"
        with codecs.open(output_file, "w", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["username", "full_name", "bio", "avatar_url", "link"])
            writer.writeheader()
            for row in profile_data:
                writer.writerow(row)

        print(f"\n✅ Hoàn tất. Đã lưu {len(profile_data)} hồ sơ vào: {output_file}")

def download_avatar(image_url, username):
    try:
        if not os.path.exists("avatars"):
            os.makedirs("avatars")
        filename = os.path.join("avatars", f"{username}.jpg")
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"🖼️ Ảnh avatar đã lưu: {filename}")
    except Exception as e:
        print(f"❌ Lỗi tải avatar cho {username}: {e}")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("⚠️ Vui lòng nhập từ khóa tìm kiếm. VD:")
        print("   python pinterest_scraper.py \"interior design\"")
        sys.exit(1)

    keyword = " ".join(sys.argv[1:])
    asyncio.run(run_pipeline(keyword))
