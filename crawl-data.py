import asyncio
import json
import csv
from playwright.async_api import async_playwright

async def fetch_user_data(page, username):
    user_data = {}

    async def handle_response(response):
        nonlocal user_data
        if "UserResource" in response.url:
            try:
                json_data = await response.json()
                if 'resource_response' in json_data and 'data' in json_data['resource_response']:
                    user_data.update(json_data['resource_response']['data'])
            except:
                pass

    page.on("response", handle_response)

    await page.goto(f"https://www.pinterest.com/{username}/", wait_until="networkidle")
    await asyncio.sleep(4)  # chờ load xong

    return {
        "username": username,
        "full_name": user_data.get("full_name"),
        "bio": user_data.get("about"),
        "avatar_url": user_data.get("image_medium_url"),
        "link": f"https://www.pinterest.com/{username}/"
        
    }

async def scrape_profiles_from_file(input_file="usernames.txt", output_file="profiles.csv"):
    # Đọc danh sách username
    with open(input_file, "r", encoding="utf-8") as f:
        usernames = [line.strip() for line in f if line.strip()]

    profile_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )
        page = await context.new_page()

        for i, username in enumerate(usernames):
            print(f"🔍 [{i+1}/{len(usernames)}] Đang lấy thông tin: {username}")
            try:
                info = await fetch_user_data(page, username)
                if info["full_name"] or info["bio"] or info["avatar_url"]:
                    profile_data.append(info)
                else:
                    print(f"⚠️ Không lấy được thông tin cho: {username}")
            except Exception as e:
                print(f"❌ Lỗi khi xử lý {username}: {e}")

        await browser.close()

    # Ghi ra file CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["username", "full_name", "bio", "avatar_url", "link"])
        writer.writeheader()
        for row in profile_data:
            writer.writerow(row)

    print(f"\n✅ Đã lưu thông tin {len(profile_data)} user vào: {output_file}")

# --- Chạy ---
if __name__ == "__main__":
    asyncio.run(scrape_profiles_from_file())
