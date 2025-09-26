from fastapi import FastAPI
from playwright.sync_api import sync_playwright

app = FastAPI()

BANK = 500  # your bankroll

@app.get("/")
def root():
    return {"ok": True, "hint": "Use /live"}

@app.get("/live")
def live_matches():
    matches = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.flashscore.com/football/")
        page.wait_for_timeout(5000)  # wait for page to load

        # Get all live matches
        games = page.query_selector_all('div.event__match')
        for g in games:
            try:
                home = g.query_selector('.event__participant--home').inner_text()
                away = g.query_selector('.event__participant--away').inner_text()
                score = g.query_selector('.event__scores').inner_text()

                if score.strip() == "0-0":  # only target 0-0
                    match_name = f"{home} vs {away}"

                    # Example stats – later can scrape shots/xG if available
                    xg = 1.0  # placeholder until Flashscore stat scraping added

                    # --- C1 ---
                    c1_score = 0.75  # TODO: fetch prematch odds and normalize
                    c1_label = "STRONG pre" if c1_score > 0.7 else "WEAK pre"

                    # --- C2 ---
                    c2_score = min(xg / 2, 1)
                    c2_label = "STRONG (HT)" if c2_score > 0.7 else "AVERAGE (HT)"

                    # --- C3 ---
                    c3_score = min(c2_score + 0.2, 1)
                    if c3_score > 0.9:
                        c3_label = "TOP PICK"
                    elif c3_score > 0.7:
                        c3_label = "GOOD PICK"
                    else:
                        c3_label = "PASS"

                    # Stake %
                    if c3_label == "TOP PICK":
                        stake = BANK * 0.2
                    elif c3_label == "GOOD PICK":
                        stake = BANK * 0.15
                    elif c3_label == "AVERAGE (HT)":
                        stake = BANK * 0.1
                    else:
                        stake = 0

                    matches.append({
                        "match": match_name,
                        "score": score,
                        "C1": {"score": c1_score, "label": c1_label},
                        "C2": {"score": c2_score, "label": c2_label},
                        "C3": {"score": c3_score, "label": c3_label},
                        "stake": f"{round(stake,2)} RON"
                    })
            except Exception:
                continue

        browser.close()

    return matches
