from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import os
import uvicorn

app = FastAPI()

# --- Example scraping function ---
def get_halftime_matches():
    """
    Scrape Flashscore for matches that are 0-0 at halftime.
    This is simplified – for production, refine selectors & add error handling.
    """
    url = "https://www.flashscore.com/football/"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    matches = []
    for match in soup.select(".event__match"):
        score = match.select_one(".event__scores")
        status = match.select_one(".event__stage")

        if score and status:
            score_text = score.get_text(strip=True)
            status_text = status.get_text(strip=True)

            if score_text == "0-0" and "HT" in status_text:
                home = match.select_one(".event__participant--home").get_text(strip=True)
                away = match.select_one(".event__participant--away").get_text(strip=True)

                matches.append({
                    "home": home,
                    "away": away,
                    "score": score_text,
                    "status": status_text
                })
    return matches

# --- Example recommendation logic ---
def run_model(match, prematch_odds=None):
    """
    Simplified logic for recommendation layers.
    Extend with Excel model rules.
    """
    recommendations = {}

    # C1 layer - prematch odds influence
    if prematch_odds:
        if prematch_odds["over05ht"] < 2.0:  # example threshold
            recommendations["C1"] = "Recommend Over 0.5 HT"
        else:
            recommendations["C1"] = "Skip"
    else:
        recommendations["C1"] = "No prematch odds data"

    # C2 layer - halftime stats (placeholder)
    recommendations["C2"] = "Stats not scraped yet (to extend)"

    # C3 layer - final recommendation
    if recommendations["C1"] == "Recommend Over 0.5 HT":
        recommendations["C3"] = "✅ Bet"
    else:
        recommendations["C3"] = "❌ No Bet"

    return recommendations


# --- API Endpoints ---
@app.get("/")
def root():
    return {"message": "Football HT 0-0 Model is running!"}

@app.get("/halftime")
def halftime():
    matches = get_halftime_matches()
    results = []
    for m in matches:
        recs = run_model(m)
        results.append({"match": m, "recommendations": recs})
    return {"results": results}


# --- Fix for Railway `$PORT` issue ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
