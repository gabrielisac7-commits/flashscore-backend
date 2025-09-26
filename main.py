from fastapi import FastAPI
from fastapi.responses import JSONResponse
import asyncio
import requests
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

app = FastAPI()

@app.get("/")
async def root():
    return {"ok": True, "hint": "Use /live"}

async def scrape_with_playwright():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.flashscore.com/football/")
        await page.wait_for_selector(".event__match")

        matches = await page.query_selector_all(".event__match")
        for match in matches[:5]:
            home = await match.query_selector(".event__participant--home")
            away = await match.query_selector(".event__participant--away")
            score = await match.query_selector(".event__scores")

            home_team = await home.inner_text() if home else "N/A"
            away_team = await away.inner_text() if away else "N/A"
            score_text = await score.inner_text() if score else "N/A"

            results.append({
                "home": home_team,
                "away": away_team,
                "score": score_text
            })

        await browser.close()
    return results

def scrape_with_requests():
    results = []
    url = "https://www.flashscore.com/football/"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        matches = soup.select(".event__match")[:5]
        for m in matches:
            home = m.select_one(".event__participant--home")
            away = m.select_one(".event__participant--away")
            score = m.select_one(".event__scores")

            results.append({
                "home": home.text if home else "N/A",
                "away": away.text if away else "N/A",
                "score": score.text if score else "N/A"
            })
    return results

@app.get("/live")
async def live_matches():
    try:
        if PLAYWRIGHT_AVAILABLE:
            data = await scrape_with_playwright()
            return {"matches": data, "note": "Playwright OK"}
        else:
            data = scrape_with_requests()
            return {"matches": data, "note": "Playwright unavailable – using requests fallback"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
