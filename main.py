import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
def root():
    return {"ok": True, "hint": "Use /live"}


@app.get("/live")
def live_matches():
    try:
        # TODO: Replace with real scraping logic
        matches = [
            {
                "match": "Chelsea vs Arsenal",
                "C1": {"score": 0.79, "label": "STRONG pre"},
                "C2": {"score": 0.78, "label": "STRONG (HT)"},
                "C3": {"score": 0.92, "label": "TOP PICK"},
                "stake": "100 RON"
            }
        ]
        return JSONResponse(content={"matches": matches})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    # Railway needs port 8080
    port = int(os.environ.get("PORT", 8080))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
