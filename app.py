import asyncio
from playwright.async_api import async_playwright

async def scrape_usernames(keyword: str, scroll_times: int = 5):
    usernames = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        search_url = f"https://www.pinterest.com/search/users/?q={keyword.replace(' ', '%20')}"
        await page.goto(search_url)
        await asyncio.sleep(3)

        # Scroll page để load thêm người
        for _ in range(scroll_times):
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2)

        # Trích xuất các <a href="/<username>/"> nằm trong khối user-rep
        elements = await page.query_selector_all('[data-test-id="user-rep"] a[href]')
        for el in elements:
            href = await el.get_attribute("href")
            if href and href.startswith("/") and len(href.strip("/").split("/")) == 1:
                username = href.strip("/")
                usernames.add(username)
        await browser.close()
        return list(usernames)

# --- Chạy thử ---
if __name__ == "__main__":
    keyword = "interior design"
    usernames = asyncio.run(scrape_usernames(keyword, scroll_times=15))
    
    # Lưu usernames vào file txt
    with open("usernames.txt", "w", encoding="utf-8") as file:
        for username in usernames:
            file.write(f"{username}\n")
