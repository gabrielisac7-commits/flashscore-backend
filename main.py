from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright
import os

app = FastAPI(title="Live 2H Goals Model", version="1.0")

# -----------------------------
# CONFIDENCE SCORE FUNCTIONS
# -----------------------------
def calc_c1(odds_home: float, odds_draw: float, odds_away: float) -> float:
    implied_prob = (1/odds_home + 1/odds_draw + 1/odds_away)
    c1 = (1/odds_home + 1/odds_away) / implied_prob
    return round(min(0.95, max(0.50, c1)), 2)

def calc_c2(shots: int, xg: float, halftime_odds: float, c1: float) -> float:
    raw = 0.4*c1 + 0.3*(shots/5) + 0.3*(xg/1.0)
    odds_adj = 1 - (halftime_odds/3.0)
    c2 = raw*0.8 + odds_adj*0.2
    return round(min(0.95, max(0.50, c2)), 2)

def calc_c3(c2: float, momentum: float, live_odds: float) -> float:
    raw = 0.6*c2 + 0.4*momentum
    odds_adj = 1 - (live_odds/3.0)
    c3 = raw*0.85 + odds_adj*0.15
    return round(min(0.99, max(0.40, c3)), 2)

def stake_from_c3(bank: float, c3: float) -> str:
    if c3 >= 0.9:
        return f"{0.2*bank:.0f} RON"
    elif c3 >= 0.75:
        return f"{0.15*bank:.0f} RON"
    elif c3 >= 0.6:
        return f"{0.1*bank:.0f} RON"
    else:
        return f"{0.05*bank:.0f} RON"

# -----------------------------
# SCRAPER
# -----------------------------
def scrape_matches() -> List[Dict[str, Any]]:
    matches = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.flashscore.com/football/", timeout=60_000)
        page.wait_for_timeout(5000)

        for g in page.query_selector_all("div.event__match"):
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
                    # Dummy stats → replace with deeper scraping if needed
                    odds_home, odds_draw, odds_away = 2.1, 3.2, 3.5
                    halftime_odds = 1.25
                    shots, xg, momentum = 5, 0.8, 0.6

                    c1 = calc_c1(odds_home, odds_draw, odds_away)
                    c2 = calc_c2(shots, xg, halftime_odds, c1)
                    c3 = calc_c3(c2, momentum, 1.28)
                    stake = stake_from_c3(500, c3)

                    matches.append({
                        "match": f"{home.inner_text().strip()} vs {away.inner_text().strip()}",
                        "status": stage_text,
                        "score": score_text,
                        "C1": c1,
                        "C2": c2,
                        "C3": c3,
                        "stake": stake,
                        "recommendation": (
                            "BET NOW" if c3 >= 0.75 else
                            "SMALL STAKE" if c3 >= 0.6 else "AVOID"
                        )
                    })
