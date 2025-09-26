import os
import uvicorn
from fastapi import FastAPI
from scraper import scrape_data
from model import load_model, predict

app = FastAPI()

# Load model once at startup
model = load_model()

@app.get("/")
def root():
    return {"status": "ok", "message": "API is running"}

@app.get("/scrape")
def scrape():
    """Scrapes fresh data from source."""
    data = scrape_data()
    return {"scraped_data": data}

@app.get("/predict")
def make_prediction(q: str):
    """
    Example prediction endpoint.
    Input: query string
    Output: model prediction
    """
    result = predict(model, q)
    return {"input": q, "prediction": result}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # platform sets $PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
