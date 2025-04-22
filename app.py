import asyncio
import random
from playwright.async_api import async_playwright

async def scrape_usernames(keyword: str, scroll_times: int = 10, output_file: str = "usernames.txt"):
    usernames = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Hiện trình duyệt
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = await context.new_page()

        search_url = f"https://www.pinterest.com/search/users/?q={keyword.replace(' ', '%20')}"
        await page.goto(search_url)
        await asyncio.sleep(3)

        for i in range(scroll_times):
            print(f"🔄 Cuộn lần {i + 1}/{scroll_times}")
            await page.mouse.wheel(0, random.randint(800, 1200))
            await asyncio.sleep(random.uniform(1.5, 2.5))

        elements = await page.query_selector_all('[data-test-id="user-rep"] a[href]')

        for el in elements:
            # Hover giả lập người dùng xem profile
            await el.hover()
            await asyncio.sleep(random.uniform(0.2, 0.5))

            href = await el.get_attribute("href")
            if href and href.startswith("/") and len(href.strip("/").split("/")) == 1:
                username = href.strip("/")
                usernames.add(username)

        await browser.close()

        # Ghi ra file
        with open(output_file, "w", encoding="utf-8") as f:
            for u in sorted(usernames):
                f.write(u + "\n")

        print(f"\n✅ Tìm được {len(usernames)} username, lưu vào {output_file}")

# --- Chạy script ---
if __name__ == "__main__":
    keyword = "interior design"  # 🎯 Tùy chỉnh từ khóa tìm kiếm tại đây
    asyncio.run(scrape_usernames(keyword, scroll_times=5))
