from fastapi import FastAPI
import random

app = FastAPI()

BANK = 500  # example bank in RON

@app.get("/")
def root():
    return {"ok": True, "hint": "Use /live"}

@app.get("/live")
def live_matches():
    # TODO: Replace this mock with Flashscore scraper
    matches = [
        {"match": "Chelsea vs Arsenal", "ht_score": "0-0", "xg": 1.2, "prematch_odds": {"1": 2.0, "X": 3.5, "2": 3.6}},
        {"match": "Barcelona vs Real Madrid", "ht_score": "0-0", "xg": 0.9, "prematch_odds": {"1": 2.4, "X": 3.4, "2": 2.9}}
    ]

    results = []
    for m in matches:
        # --- C1: prematch strength ---
        avg_odds = (m["prematch_odds"]["1"] + m["prematch_odds"]["2"]) / 2
        c1_score = round(1 - (avg_odds / 10), 2)  # simple normalization
        c1_label = "STRONG pre" if c1_score > 0.7 else "WEAK pre"

        # --- C2: halftime stats ---
        c2_score = round(min(m["xg"] / 2, 1), 2)
        c2_label = "STRONG (HT)" if c2_score > 0.7 else "AVERAGE (HT)"

        # --- C3: min 60 adjusted (simulate with boost) ---
        c3_score = round(min(c2_score + random.uniform(0.1, 0.3), 1), 2)
        if c3_score > 0.9:
            c3_label = "TOP PICK"
        elif c3_score > 0.7:
            c3_label = "GOOD PICK"
        else:
            c3_label = "PASS"

        # --- Stake recommendation ---
        if c3_label == "TOP PICK":
            stake = round(BANK * 0.2, 2)
        elif c3_label == "GOOD PICK":
            stake = round(BANK * 0.15, 2)
        elif c3_label == "AVERAGE (HT)":
            stake = round(BANK * 0.1, 2)
        else:
            stake = 0

        results.append({
            "match": m["match"],
            "C1": {"score": c1_score, "label": c1_label},
            "C2": {"score": c2_score, "label": c2_label},
            "C3": {"score": c3_score, "label": c3_label},
            "stake": f"{stake} RON"
        })

    return results
