from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict
import joblib
import numpy as np
import os

from playwright.sync_api import sync_playwright

# -----------------------------
# Load the trained model
# -----------------------------
MODEL_PATH = "final_model.pkl"

if not os.path.exists(MODEL_PATH):
    raise RuntimeError("Model file not found. Make sure final_model.pkl is in /app.")

model = joblib.load(MODEL_PATH)

# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI(title="Football Prediction API", version="1.0")

class PredictionRequest(BaseModel):
    home_team: str
    away_team: str
    features: List[float]

class PredictionResponse(BaseModel):
    home_team: str
    away_team: str
    prediction: str
    probabilities: Dict[str, float]


# -----------------------------
# Helper: scrape live matches
# -----------------------------
def scrape_live_matches():
    matches = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Example: Flashscore live matches
        page.goto("https://www.flashscore.com/football/")
        page.wait_for_timeout(5000)

        # Extract match info
        match_elements = page.query_selector_all(".event__match")
        for m in match_elements:
            home = m.query_selector(".event__participant--home")
            away = m.query_selector(".event__participant--away")
            score = m.query_selector(".event__scores")

            if home and away:
                matches.append({
                    "home": home.inner_text().strip(),
                    "away": away.inner_text().strip(),
                    "score": score.inner_text().strip() if score else "0-0"
                })

        browser.close()
    return matches


# -----------------------------
# API Endpoints
# -----------------------------

@app.get("/")
def root():
    return {"status": "ok", "message": "Football Prediction API is running 🚀"}


@app.get("/live")
def live_matches():
    try:
        matches = scrape_live_matches()
        return {"count": len(matches), "matches": matches}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest):
    # Model expects numerical features
    X = np.array(req.features).reshape(1, -1)
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0]

    result = PredictionResponse(
        home_team=req.home_team,
        away_team=req.away_team,
        prediction=pred,
        probabilities={
            "home_win": float(proba[0]),
            "draw": float(proba[1]),
            "away_win": float(proba[2]),
        },
    )
    return result
