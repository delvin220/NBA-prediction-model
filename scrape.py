import os
import time
import asyncio
import ctypes
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Prevent sleep while script runs (Windows only)
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

# Constants
SEASONS = list(range(2021, 2026))
DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")

# Ensure directories exist
os.makedirs(STANDINGS_DIR, exist_ok=True)
os.makedirs(SCORES_DIR, exist_ok=True)

print("Saving to:")
print("Standings:", STANDINGS_DIR)
print("Scores:", SCORES_DIR)

# Fetch HTML with retries
async def get_html(url, selector, sleep=5, retries=3):
    html = None
    for i in range(1, retries + 1):
        time.sleep(sleep * i)
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto(url)
                print("Title:", await page.title())
                html = await page.inner_html(selector)
        except PlaywrightTimeout:
            print(f"Timeout on {url}")
            continue
        else:
            break
    return html

# Scrape schedule pages for a season
async def scrape_season(season):
    print(f"\nScraping season {season}")
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games.html"
    html = await get_html(url, "#content .filter")

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    href = [l["href"] for l in links]
    standings_pages = [f"https://www.basketball-reference.com{l}" for l in href]

    for url in standings_pages:
        filename = url.split("/")[-1]
        save_path = os.path.join(STANDINGS_DIR, filename)
        if os.path.exists(save_path):
            continue
        html = await get_html(url, "#all_schedule")
        if html:
            with open(save_path, "w+", encoding="utf-8") as f:
                f.write(html)
            print("Saved:", save_path)

# Scrape individual game box scores
async def scrape_game(standings_file):
    with open(standings_file, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a")
    hrefs = [l.get("href") for l in links]
    box_scores = [
        f"https://www.basketball-reference.com{l}"
        for l in hrefs if l and "boxscore" in l and ".html" in l
    ]

    for url in box_scores:
        filename = url.split("/")[-1]
        save_path = os.path.join(SCORES_DIR, filename)
        if os.path.exists(save_path):
            continue
        html = await get_html(url, "#content")
        if html:
            with open(save_path, "w+", encoding="utf-8") as f:
                f.write(html)
            print("Box score saved:", save_path)

# Async runner
async def main():
    for season in SEASONS:
        await scrape_season(season)

    standings_files = [
        os.path.join(STANDINGS_DIR, f)
        for f in os.listdir(STANDINGS_DIR)
        if f.endswith(".html")
    ]

    for file in standings_files:
        await scrape_game(file)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
    # Allow sleep again after script ends
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
