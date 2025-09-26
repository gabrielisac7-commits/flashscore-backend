from fastapi import FastAPI, Query
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

app = FastAPI()

BASE_URL = "https://www.flashscore.com"
BANK_RON = 500  # staking bank

# ----------------- MODEL (same logic you approved) -----------------
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
                       mom_shots: float, mom_sot: float, mom_xg: float,
                       risk: float = 0, ev_now: float = 0, ev60: float = 0):
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
    return round(c3, 2), label

def stake_ron(final_label: str, ht_exception: bool = False) -> int:
    if ht_exception: return int(BANK_RON * 0.20)
    lab = (final_label or "").upper()
    if "TOP PICK" in lab: return int(BANK_RON * 0.20)
    if "BET NOW"  in lab: return int(BANK_RON * 0.15)
    if "SMALL"    in lab: return int(BANK_RON * 0.10)
    if "BORDERLINE" in lab: return int(BANK_RON * 0.05)
    return 0

# --------------- SCRAPER HELPERS (Playwright) ----------------------
def text_or_none(el) -> Optional[str]:
    try:
        if el:
            t = el.inner_text().strip()
            return t if t else None
    except Exception:
        return None
    return None

def parse_int(s: Optional[str]) -> int:
    if not s: return 0
    s = s.replace("\u00a0", "").strip()
    try: return int(s)
    except: return 0

def parse_float(s: Optional[str]) -> Optional[float]:
    if not s: return None
    s = s.replace(",", ".").strip()
    try: return float(s)
    except: return None

def get_zero_zero_ht_matches(page):
    page.goto(f"{BASE_URL}/matches/", timeout=60000)
    page.wait_for_selector("div.event__match", timeout=60000)
    items = page.query_selector_all("div.event__match")
    results = []
    for m in items:
        score = text_or_none(m.query_selector("div.event__scores"))
        stage = text_or_none(m.query_selector("div.event__stage"))
        home  = text_or_none(m.query_selector(".event__participant--home"))
        away  = text_or_none(m.query_selector(".event__participant--away"))
        mid   = m.get_attribute("id")
        if not (score and stage and mid): continue
        if "0 - 0" in score and ("Half" in stage or "HT" in stage):
            match_id = mid.split("_")[-1]
            results.append({
                "id": match_id,
                "home": home or "Home",
                "away": away or "Away",
                "score": score,
                "status": stage
            })
    return results

def grab_ht_stats(page, match_id) -> Dict[str, Any]:
    # Shots / SOT / xG (if available)
    url = f"{BASE_URL}/match/{match_id}/#match-summary"
    page.goto(url, timeout=60000)
    page.wait_for_selector("div#summary-content, div#tab-statistics-0-statistic", timeout=60000)
    rows = page.query_selector_all("div.stat__row")
    shots = sot = 0
    xg_h = xg_a = 0.0
    for r in rows:
        cat = (text_or_none(r.query_selector(".stat__category")) or "").lower()
        hv = text_or_none(r.query_selector(".stat__homeValue"))
        av = text_or_none(r.query_selector(".stat__awayValue"))
        if "shots on target" in cat or "shots on goal" in cat:
            sot = parse_int(hv) + parse_int(av)
        elif cat == "shots":
            shots = parse_int(hv) + parse_int(av)
        elif "expected" in cat or "xg" in cat:
            xg_h = parse_float(hv) or 0.0
            xg_a = parse_float(av) or 0.0
    return {"shots": shots, "sot": sot, "xg": round(xg_h + xg_a, 2)}

def grab_prematch_odds(page, match_id) -> Dict[str, Any]:
    # Over/Under 0.5 and 1X2 pre-match where available
    out = {"o05": None, "hda": [None, None, None]}

    # 1X2
    page.goto(f"{BASE_URL}/match/{match_id}/#odds-comparison;1x2;full-time", timeout=60000)
    # Take the first row of odds cells we see
    try:
        row = page.query_selector("div.ui-table__row")
        if row:
            cells = row.query_selector_all("div.ui-table__cell")
            # Many books include additional columns; the first 3 odds are usually H/D/A
            if len(cells) >= 4:
                h = parse_float(text_or_none(cells[1]))
                d = parse_float(text_or_none(cells[2]))
                a = parse_float(text_or_none(cells[3]))
                out["hda"] = [h, d, a]
    except Exception:
        pass

    # Over/Under 0.5
    page.goto(f"{BASE_URL}/match/{match_id}/#odds-comparison;over-under;full-time", timeout=60000)
    try:
        rows = page.query_selector_all("div.ui-table__row")
        for r in rows:
            ttl = text_or_none(r.query_selector("div.ui-table__title")) or ""
            if "0.5" in ttl:
                cells = r.query_selector_all("div.ui-table__cell")
                if len(cells) >= 2:
                    out["o05"] = parse_float(text_or_none(cells[1]))
                    break
    except Exception:
        pass

    return out

# ------------------------ API ENDPOINT -----------------------------
@app.get("/live")
def live_matches(ht_odds: Optional[float] = Query(default=None, description="Manual Over 0.5 odds at HT (optional)")):
    """
    Returns only matches that are 0-0 at Half Time with model outputs.
    Optional: ?ht_odds=1.18 to override/force HT odds if scraping doesn't show them.
    """
    results: List[Dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # 0-0 HT filter
            games = get_zero_zero_ht_matches(page)

            for g in games:
                # Grab stats and odds
                stats = grab_ht_stats(page, g["id"])
                odds  = grab_prematch_odds(page, g["id"])

                # MODEL
                c1, l1 = confidence_score_1(odds.get("o05"), *(odds.get("hda") or [None,None,None]))
                c2, l2 = confidence_score_2(c1, stats["shots"], stats["sot"], stats["xg"], ht_odds=ht_odds)
                # At exact HT we may not have 46–60 yet → projection: momentum 0
                c3, l3 = confidence_score_3(c1, c2, mom_shots=0, mom_sot=0, mom_xg=0.0)

                stake = stake_ron(l3)
                results.append({
                    "match": f"{g['home']} vs {g['away']}",
                    "league_status": g["status"],
                    "score": g["score"],
                    "odds": {"o05": odds.get("o05"), "hda": odds.get("hda")},
                    "ht_stats": stats,
                    "C1": {"score": c1, "label": l1},
                    "C2": {"score": c2, "label": l2},
                    "C3": {"score": c3, "label": l3},
                    "stake_RON": stake,
                    "urls": {
                        "summary": f"{BASE_URL}/match/{g['id']}/#match-summary",
                        "odds_ou": f"{BASE_URL}/match/{g['id']}/#odds-comparison;over-under;full-time",
                        "odds_1x2": f"{BASE_URL}/match/{g['id']}/#odds-comparison;1x2;full-time",
                    }
                })
        finally:
            browser.close()
    return results

@app.get("/")
def root():
    return {"ok": True, "hint": "Use /live (optionally ?ht_odds=1.18)"}
