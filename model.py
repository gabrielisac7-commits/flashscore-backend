# model.py - final version placeholder with real logic

import joblib
import os

MODEL_PATH = "model.pkl"

def load_model():
    """Loads your trained ML model from file (update with your real model)."""
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        return model
    else:
        # Mock model if none exists yet
        return {"type": "mock"}

def predict(model, text: str):
    """Runs prediction using the model."""
    if model == {"type": "mock"}:
        return f"Mock prediction for: {text}"
    else:
        # Replace with your real model inference
        return model.predict([text])[0]

