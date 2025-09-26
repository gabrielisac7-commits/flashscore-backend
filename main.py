from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup

app = FastAPI()

BASE_URL = "https://www.flashscore.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}
BANK = 500  # RON

# --- Model functions (simplified) ---

def confidence_score_1(o05_odds, home_odds, draw_odds, away_odds):
    if not o05_odds or not home_odds:
        return None, "—"
    p_o05 = 1 / o05_odds
    total = 1/home_odds + 1/draw_odds + 1/away_odds
    fav_strength = max(1/home_odds, 1/away_odds) / total
    c1 = 0.6*p_o05 + 0.4*fav_strength
    c1 = max(0.05, min(0.95, c1))
    if c1 >= 0.80: label = "ELITE pre"
    elif c1 >= 0.75: label = "STRONG pre"
    elif c1 >= 0.70: label = "GOOD pre"
    elif c1 >= 0.60: label = "WEAK pre"
    else: label = "BAD pre"
    return round(c1,2), label

def confidence_score_2(c1, shots, sot, xg, ht_odds=None):
    if c1 is None: return None, "—"
    shots = shots or 0; sot = sot or 0; xg = xg or 0
    vol_ht = min(1, 0.40*(shots/8) + 0.35*(sot/5) + 0.25*(xg/1.6))
    qual_ht = min(1, max(0, (xg/sot - 0.10)/0.20)) if sot > 0 else 0
    align = 0.5
    if ht_odds and ht_odds > 1:
        implied = 1/ht_odds
        align = max(0, 1 - abs(c1 - implied)/0.30)
    c2 = 0.30*c1 + 0.45*vol_ht + 0.15*qual_ht + 0.10*align
    c2 = max(0.05, min(0.90, c2))
    if c2 >= 0.80: label = "ELITE (HT)"
    elif c2 >= 0.75: label = "STRONG (HT)"
    elif c2 >= 0.70: label = "BORDERLINE (HT)"
    elif c2 >= 0.60: label = "WEAK (HT)"
    else: label = "DEAD (HT)"
    return round(c2,2), label

def confidence_score_3(c1, c2, mom_shots, mom_sot, mom_xg, risk=0, ev_now=0, ev60=0):
    if c1 is None or c2 is None: return None, "—"
    base = 0.5*c1 + 0.5*c2
    momentum = 0.1*mom_shots + 0.2*mom_sot + 0.7*mom_xg
    c3 = base + momentum
    if risk >= 40 or max(ev_now, ev60) < 0: c3 -= 0.10
    c3 = max(0.05, min(0.92, c3))
    if c3 >= 0.85: label = "TOP PICK"
    elif c3 >= 0.80: label = "BET NOW"
    elif c3 >= 0.75: label = "SMALL STAKE"
    elif c3 >= 0.70: label = "BORDERLINE"
    else: label = "AVOID"
    return round(c3,2), label

def stake_units(rec, ht_exception=False):
    if ht_exception: return int(BANK*0.20)
    rec = rec.upper()
    if "TOP PICK" in rec: return int(BANK*0.20)
    if "BET NOW" in rec: return int(BANK*0.15)
    if "SMALL" in rec: return int(BANK*0.10)
    if "BORDERLINE" in rec: return int(BANK*0.05)
    return 0

# --- Example endpoint ---

@app.get("/live")
def live_matches():
    # For demo: return fake game until scraper selectors are fine-tuned
    c1, l1 = confidence_score_1(1.12, 1.50, 4.20, 6.50)
    c2, l2 = confidence_score_2(c1, shots=8, sot=4, xg=0.9, ht_odds=1.18)
    c3, l3 = confidence_score_3(c1, c2, mom_shots=3, mom_sot=2, mom_xg=0.35)
    stake = stake_units(l3)

    return [{
        "match": "Chelsea vs Arsenal",
        "C1": {"score": c1, "label": l1},
        "C2": {"score": c2, "label": l2},
        "C3": {"score": c3, "label": l3},
        "stake": f"{stake} RON"
    }]
