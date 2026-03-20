from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import requests as http_requests

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.tithi import (
    TithiInfo, NakshatraInfo,
    find_next_tithi_boundary, find_next_nakshatra_boundary,
    get_day_tithi_segments_singapore,
    tithi_at, nakshatra_at, yoga_at, karana_at, get_tamil_month,
    NALLA_NERAM, GOWRI_NALLA_NERAM,
)

app = FastAPI(
    title="SG Panchang API",
    description="Singapore Panchanga API — Lahiri Ayanamsa, SGT (UTC+8)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

SG_TZ = ZoneInfo("Asia/Singapore")


# ── Health ──────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timezone": "Asia/Singapore"}


# ── Sunrise (live from sunrise-sunset.org) ──────────────
@app.get("/sunrise")
def get_sunrise(date: str = None):
    now_sg = datetime.now(SG_TZ)
    query_date = date or now_sg.strftime("%Y-%m-%d")
    try:
        resp = http_requests.get(
            "https://api.sunrise-sunset.org/json",
            params={
                "lat": 1.3521, "lng": 103.8198,
                "date": query_date,
                "tzid": "Asia/Singapore",
                "formatted": 0,
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()["results"]

        def parse_iso(s):
            d = datetime.fromisoformat(s)
            return d.strftime("%H:%M"), round(d.hour + d.minute/60 + d.second/3600, 4)

        sunrise_str, sunrise_h = parse_iso(data["sunrise"])
        sunset_str,  sunset_h  = parse_iso(data["sunset"])
        noon_str,    noon_h    = parse_iso(data["solar_noon"])

        day_dur = sunset_h - sunrise_h

        # Nalla Neram — based on weekday and real sunrise
        wd = datetime.fromisoformat(query_date).weekday()  # 0=Mon in Python
        # Convert to Tamil weekday (0=Sun)
        sg_date = now_sg if not date else datetime.fromisoformat(date).replace(tzinfo=SG_TZ)
        tamil_wd = sg_date.weekday()  # 0=Mon; we need 0=Sun
        wd_sun = (tamil_wd + 1) % 7   # 0=Sun, 1=Mon...

        def calc_period(portion, dur_h):
            start = sunrise_h + (portion - 1) * (day_dur / 8)
            end   = start + dur_h
            sh = int(start) % 24; sm = round((start % 1) * 60)
            eh = int(end)   % 24; em = round((end   % 1) * 60)
            if sm == 60: sh += 1; sm = 0
            if em == 60: eh += 1; em = 0
            ampm_s = "AM" if sh < 12 else "PM"
            ampm_e = "AM" if eh < 12 else "PM"
            sh12 = sh % 12 or 12; eh12 = eh % 12 or 12
            return f"{sh12:02d}:{sm:02d} {ampm_s} - {eh12:02d}:{em:02d} {ampm_e}"

        nalla   = [calc_period(p, d) for p, d in NALLA_NERAM.get(wd_sun, [])]
        gowri   = [calc_period(p, d) for p, d in GOWRI_NALLA_NERAM.get(wd_sun, [])]

        return {
            "date":         query_date,
            "source":       "sunrise-sunset.org",
            "sunrise_sgt":  sunrise_str,
            "sunset_sgt":   sunset_str,
            "noon_sgt":     noon_str,
            "sunrise_h":    sunrise_h,
            "sunset_h":     sunset_h,
            "noon_h":       noon_h,
            "nalla_neram":  nalla,
            "gowri_nalla_neram": gowri,
        }
    except Exception as e:
        return {
            "date": query_date, "source": "fallback",
            "sunrise_sgt": "07:09", "sunset_sgt": "19:15", "noon_sgt": "13:12",
            "sunrise_h": 7.15, "sunset_h": 19.25, "noon_h": 13.20,
            "nalla_neram": [], "gowri_nalla_neram": [],
            "error": str(e),
        }


# ── Tithi Now ────────────────────────────────────────────
@app.get("/tithi-now")
def get_tithi_now():
    now_sg  = datetime.now(SG_TZ)
    now_utc = now_sg.astimezone(timezone.utc)

    current       = tithi_at(now_utc)
    nak           = nakshatra_at(now_utc)
    yoga          = yoga_at(now_utc)
    karana        = karana_at(now_utc)
    tamil_month   = get_tamil_month(now_utc)

    next_tithi_boundary = find_next_tithi_boundary(now_utc).astimezone(SG_TZ)
    next_nak_boundary   = find_next_nakshatra_boundary(now_utc).astimezone(SG_TZ)

    time_left  = next_tithi_boundary - now_sg
    hours_left = int(time_left.total_seconds() // 3600)
    mins_left  = int((time_left.total_seconds() % 3600) // 60)

    return {
        "now_sgt": now_sg.strftime("%Y-%m-%d %H:%M:%S SGT"),
        "tamil_month": tamil_month,
        "tithi": {
            "index":            current.index + 1,
            "name":             current.name,
            "name_tamil":       current.name_tamil,
            "paksha":           current.paksha,
            "elongation_deg":   current.elongation,
            "ends_at_sgt":      next_tithi_boundary.strftime("%I:%M %p SGT"),
            "ends_at_sgt_iso":  next_tithi_boundary.isoformat(),
            "time_remaining":   f"{hours_left}h {mins_left}m",
        },
        "nakshatra": {
            "index":        nak.index + 1,
            "name":         nak.name,
            "name_tamil":   nak.name_tamil,
            "pada":         nak.pada,
            "ends_at_sgt":  next_nak_boundary.strftime("%I:%M %p SGT"),
            "ends_at_sgt_iso": next_nak_boundary.isoformat(),
        },
        "yoga":   yoga,
        "karana": karana,
    }


# ── Tithi for date ───────────────────────────────────────
@app.get("/tithi")
def get_tithi_for_date(
    date: str = Query(..., description="YYYY-MM-DD in Singapore time", example="2026-03-20")
):
    try:
        datetime.fromisoformat(date)
    except ValueError:
        return {"error": "Invalid date. Use YYYY-MM-DD"}
    segments = get_day_tithi_segments_singapore(date)
    return {
        "date": date, "timezone": "Asia/Singapore (SGT, UTC+8)",
        "tithi_count": len(segments), "segments": segments,
    }


# ── Root ─────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": "SG Panchang API v2",
        "endpoints": {
            "GET /tithi-now":             "Full panchanga right now",
            "GET /tithi?date=YYYY-MM-DD": "Tithi segments for a date",
            "GET /sunrise":               "Sunrise/sunset + Nalla Neram today",
            "GET /sunrise?date=YYYY-MM-DD": "Sunrise for a specific date",
            "GET /health":                "Health check",
            "GET /docs":                  "Swagger UI",
        }
    }
