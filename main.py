from fastapi import FastAPI, Query
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

app = FastAPI()

BASE_URL = "https://www.flashscore.com"
BANK_RON = 500  # your bankroll for staking


# ----------------- MODEL -----------------
def confidence_score_1(o05_odds: Optional[float],
                       home_odds: Optional[float],
                       draw_odds: Optional[float],
                       away_odds: Optional[float]):
    if not o05_odds or not home_odds or not draw_odds or not away_odds:
        return None, "—"

    p_o05 = 1.0 / o05_odds
    total = 1.0/home_odds + 1.0/draw_odds + 1.0/away_odds
    fav_strength = max(1.0/home_odds, 1.0/away_odds) / total

    c1 = 0.6 * p_o05 + 0.4 * fav_strength
    c1 = max(0.05, min(0.95, c1))

    if c1 >= 0.80: label = "ELITE pre"
    elif c1 >= 0.75: label = "STRONG pre"
    elif c1 >= 0.70: label = "GOOD pre"
    elif c1 >= 0.60: label = "WEAK pre"
    else: label = "BAD pre"

    return round(c1, 2), label


def confidence_score_2(c1: Optional[float], shots: float, sot: float, xg: float,
                       ht_odds: Optional[float] = None):
    if c1 is None: return None, "—"
    shots = shots or 0; sot = sot or 0; xg = xg or 0

    vol_ht = min(1, 0.40*(shots/8) + 0.35*(sot/5) + 0.25*(xg/1.6))
    qual_ht = min(1, max(0, (xg/sot - 0.10)/0.20)) if sot > 0 else 0

    align = 0.5
    if ht_odds and ht_odds > 1:
        implied = 1.0/ht_odds
        align = max(0, 1 - abs(c1 - implied)/0.30)

    c2 = 0.30*c1 + 0.45*vol_ht + 0.15*qual_ht + 0.10*align
    c2 = max(0.05, min(0.90, c2))

    if c2 >= 0.80: label = "ELITE (HT)"
    elif c2 >= 0.75: label = "STRONG (HT)"
    elif c2 >= 0.70: label = "BORDERLINE (HT)"
    elif c2 >= 0.60: label = "WEAK (HT)"
    else: label = "DEAD (HT)"

    return round(c2, 2), label


def confidence_score_3(c1: Optional[float], c2: Optional[float],
                       mom_shots: float, mom_sot: float, mom_xg: float):
    if c1 is None or c2 is None: return None, "—"

    base = 0.5*c1 + 0.5*c2
    momentum = 0.1*mom_shots + 0.2*mom_sot + 0.7*mom_xg
    c3 = base + momentum
    c3 = max(0.05, min(0.92, c3))

    if c3 >= 0.85: label = "TOP PICK"
    elif c3 >= 0.80: label = "BET NOW"
    elif c3 >= 0.75: label = "SMALL STAKE"
    elif c3 >= 0.70: label = "BORDERLINE"
    else: label = "AVOID"

    return round(c3, 2), label


def stake_units(label: str) -> int:
    if not label: return 0
    label = label.upper()
    if "TOP PICK" in label: return int(BANK_RON*0.20)
    if "BET NOW" in label: return int(BANK_RON*0.15)
    if "SMALL" in label: return int(BANK_RON*0.10)
    if "BORDERLINE" in label: return int(BANK_RON*0.05)
    return 0


# ----------------- SCRAPER HELPERS -----------------
def get_zero_zero_ht_matches(page):
    page.goto(f"{BASE_URL}/matches/", timeout=60000)
    page.wait_for_selector("div.event__match", timeout=60000)

    items = page.query_selector_all("div.event__match")
    results = []
    for m in items:
        score = m.inner_text() if m.query_selector(".event__scores") else None
        stage = m.inner_text() if m.query_selector(".event__stage") else None
        home  = m.query_selector(".event__participant--home")
        away  = m.query_selector(".event__participant--away")

        if score and "0 - 0" in score and stage and "Half" in stage:
            match_id = m.get_attribute("id").split("_")[-1]
            results.append({
                "id": match_id,
                "home": home.inner_text().strip() if home else "Home",
                "away": away.inner_text().strip() if away else "Away",
                "score": score,
                "status": stage
            })
    return results


# ----------------- API -----------------
@app.get("/")
def root():
    return {"ok": True, "hint": "Use /live"}


@app.get("/live")
def live_matches(ht_odds: Optional[float] = Query(default=None)):
    results: List[Dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            games = get_zero_zero_ht_matches(page)
            for g in games:
                # TODO: Extend here → grab odds/stats from match page
                # Right now: demo numbers
                shots, sot, xg = 8, 3, 0.9
                o05 = 1.18
                hda = [1.50, 4.20, 6.50]

                c1, l1 = confidence_score_1(o05, *hda)
                c2, l2 = confidence_score_2(c1, shots, sot, xg, ht_odds=ht_odds)
                c3, l3 = confidence_score_3(c1, c2, 0, 0, 0)
                stake = stake_units(l3)

                results.append({
                    "match": f"{g['home']} vs {g['away']}",
                    "score": g["score"],
                    "status": g["status"],
                    "C1": {"score": c1, "label": l1},
                    "C2": {"score": c2, "label": l2},
                    "C3": {"score": c3, "label": l3},
                    "stake": f"{stake} RON"
                })
        finally:
            browser.close()
    return results
