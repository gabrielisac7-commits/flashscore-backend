import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import List, Dict, Any

# Ensure Playwright uses the same path at runtime
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/app/.cache/ms-playwright")

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "hint": "Use /live"}

def scrape_with_playwright() -> List[Dict[str, Any]]:
    from playwright.sync_api import sync_playwright
    data: List[Dict[str, Any]] = []
    with sync_playwright() as p:
        # if Chromium still isn't found, this line would crash without our try/except in /live
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.flashscore.com/football/", timeout=60_000)
        page.wait_for_timeout(4000)

        # Basic example: collect 0–0 HT games (you can expand selectors later)
        games = page.query_selector_all("div.event__match")
        for g in games:
            try:
                stage = g.query_selector(".event__stage")
                score = g.query_selector(".event__scores")
                home = g.query_selector(".event__participant--home")
                away = g.query_selector(".event__participant--away")
                if not (stage and score and home and away):
                    continue
                stage_text = stage.inner_text().strip()
                score_text = score.inner_text().strip()
                if ("Half" in stage_text or "HT" in stage_text) and score_text == "0-0":
                    data.append({
                        "match": f"{home.inner_text().strip()} vs {away.inner_text().strip()}",
                        "status": stage_text,
                        "score": score_text,
                        "source_mode": "playwright"
                    })
            except Exception:
                continue
        browser.close()
    return data

def scrape_with_requests() -> List[Dict[str, Any]]:
    # Lightweight fallback (no JS) – won’t see everything, but avoids 500s
    import requests
    from bs4 import BeautifulSoup
    r = requests.get("https://www.flashscore.com/football/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    data: List[Dict[str, Any]] = []
    for g in soup.select("div.event__match"):
        stage = g.select_one(".event__stage")
        score = g.select_one(".event__scores")
        home  = g.select_one(".event__participant--home")
        away  = g.select_one(".event__participant--away")
        if not (stage and score and home and away):
            continue
        stage_text = stage.get_text(strip=True)
        score_text = score.get_text(strip=True)
        if ("Half" in stage_text or "HT" in stage_text) and score_text == "0-0":
            data.append({
                "match": f"{home.get_text(strip=True)} vs {away.get_text(strip=True)}",
                "status": stage_text,
                "score": score_text,
                "source_mode": "requests-fallback"
            })
    return data

@app.get("/live")
def live():
    try:
        # Try full scraper first
        try:
            data = scrape_with_playwright()
        except Exception as e:
            # If Chromium not found or launch fails, use fallback
            data = scrape_with_requests()
            return {"matches": data, "note": "Playwright unavailable – using requests fallback"}
        return {"matches": data}
    except Exception as e:
        # Never 500 to the user; return a clear JSON error instead
        return JSONResponse(status_code=200, content={"matches": [], "error": str(e)})
