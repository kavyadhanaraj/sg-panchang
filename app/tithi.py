from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import swisseph as swe

SG_TZ = ZoneInfo("Asia/Singapore")

# Set Lahiri ayanamsa (Thirukanitham standard)
swe.set_sid_mode(swe.SIDM_LAHIRI)

TITHI_NAMES = [
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya",
]

TITHI_NAMES_TAMIL = [
    "பிரதமை","துவிதியை","திருதியை","சதுர்த்தி","பஞ்சமி",
    "சஷ்டி","சப்தமி","அஷ்டமி","நவமி","தசமி",
    "ஏகாதசி","துவாதசி","திரயோதசி","சதுர்தசி","பூர்ணிமை",
    "பிரதமை","துவிதியை","திருதியை","சதுர்த்தி","பஞ்சமி",
    "சஷ்டி","சப்தமி","அஷ்டமி","நவமி","தசமி",
    "ஏகாதசி","துவாதசி","திரயோதசி","சதுர்தசி","அமாவாசை",
]

NAKSHATRA_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni",
    "Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha",
    "Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana",
    "Dhanishtha","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati",
]

NAKSHATRA_NAMES_TAMIL = [
    "அஸ்வினி","பரணி","கார்த்திகை","ரோகிணி","மிருகசீர்ஷம்","திருவாதிரை",
    "புனர்பூசம்","பூசம்","ஆயில்யம்","மகம்","பூரம்",
    "உத்திரம்","அஸ்தம்","சித்திரை","சுவாதி","விசாகம்","அனுஷம்",
    "கேட்டை","மூலம்","பூராடம்","உத்திராடம்","திருவோணம்",
    "அவிட்டம்","சதயம்","பூரட்டாதி","உத்திரட்டாதி","ரேவதி",
]

YOGA_NAMES = [
    "Vishkambha","Preeti","Ayushman","Saubhagya","Shobhana",
    "Atiganda","Sukarma","Dhriti","Shula","Ganda",
    "Vriddhi","Dhruva","Vyaghata","Harshana","Vajra",
    "Siddhi","Vyatipata","Variyana","Parigha","Shiva",
    "Siddha","Sadhya","Shubha","Shukla","Brahma",
    "Indra","Vaidhriti",
]

KARANA_NAMES = [
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Shakuni","Chatushpada","Naga","Kimstughna",
]

TAMIL_MONTHS = [
    "சித்திரை","வைகாசி","ஆனி","ஆடி","ஆவணி","புரட்டாசி",
    "ஐப்பசி","கார்த்திகை","மார்கழி","தை","மாசி","பங்குனி",
]

NALLA_NERAM = {
    0: [(7, 1.5), (4, 1.5)],
    1: [(2, 1.5), (6, 1.5)],
    2: [(6, 1.5), (3, 1.5)],
    3: [(5, 1.5), (7, 1.5)],
    4: [(3, 1.5), (5, 1.5)],
    5: [(1, 1.5), (2, 1.5)],
    6: [(4, 1.5), (1, 1.5)],
}

GOWRI_NALLA_NERAM = {
    0: [(5, 1.5), (2, 1.5)],
    1: [(4, 1.5), (1, 1.5)],
    2: [(3, 1.5), (7, 1.5)],
    3: [(2, 1.5), (6, 1.5)],
    4: [(1, 1.5), (5, 1.5)],
    5: [(7, 1.5), (4, 1.5)],
    6: [(6, 1.5), (3, 1.5)],
}


@dataclass
class TithiInfo:
    index: int
    name: str
    name_tamil: str
    elongation: float
    paksha: str


@dataclass
class NakshatraInfo:
    index: int
    name: str
    name_tamil: str
    pada: int


def to_julian_day(dt_utc: datetime) -> float:
    if dt_utc.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    dt_utc = dt_utc.astimezone(timezone.utc)
    h = (dt_utc.hour + dt_utc.minute / 60
         + dt_utc.second / 3600
         + dt_utc.microsecond / 3_600_000_000)
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h)


def _moon_sidereal_lon(dt_utc: datetime) -> float:
    """Return Moon's sidereal longitude using Swiss Ephemeris (Lahiri)."""
    jd = to_julian_day(dt_utc)
    return swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)[0][0] % 360


def _sun_sidereal_lon(dt_utc: datetime) -> float:
    """Return Sun's sidereal longitude using Swiss Ephemeris (Lahiri)."""
    jd = to_julian_day(dt_utc)
    return swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)[0][0] % 360


def sun_moon_sidereal(dt_utc: datetime):
    jd = to_julian_day(dt_utc)
    sun  = swe.calc_ut(jd, swe.SUN,  swe.FLG_SIDEREAL)[0][0] % 360
    moon = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)[0][0] % 360
    return sun, moon


def elongation_deg(dt_utc: datetime) -> float:
    sun_lon, moon_lon = sun_moon_sidereal(dt_utc)
    return (moon_lon - sun_lon) % 360


def tithi_at(dt_utc: datetime) -> TithiInfo:
    e = elongation_deg(dt_utc)
    idx = int(math.floor(e / 12.0)) % 30
    paksha = "Shukla" if idx < 15 else "Krishna"
    return TithiInfo(
        index=idx,
        name=TITHI_NAMES[idx],
        name_tamil=TITHI_NAMES_TAMIL[idx],
        elongation=round(e, 4),
        paksha=paksha,
    )


def nakshatra_at(dt_utc: datetime) -> NakshatraInfo:
    """
    Calculate nakshatra from Moon's sidereal longitude.
    Each nakshatra = 360/27 = 13.3333...degrees
    Uses Swiss Ephemeris with Lahiri ayanamsa for accuracy.
    """
    moon = _moon_sidereal_lon(dt_utc)
    nak_span = 360.0 / 27.0          # 13.33333...
    idx  = int(moon / nak_span) % 27
    pada = int((moon % nak_span) / (nak_span / 4.0)) + 1
    return NakshatraInfo(
        index=idx,
        name=NAKSHATRA_NAMES[idx],
        name_tamil=NAKSHATRA_NAMES_TAMIL[idx],
        pada=pada,
    )


def yoga_at(dt_utc: datetime) -> dict:
    sun_lon, moon_lon = sun_moon_sidereal(dt_utc)
    total = (sun_lon + moon_lon) % 360
    idx = int(total / (360.0 / 27.0)) % 27
    return {"index": idx + 1, "name": YOGA_NAMES[idx]}


def karana_at(dt_utc: datetime) -> dict:
    e = elongation_deg(dt_utc)
    idx = int(e / 6.0) % 60
    name = KARANA_NAMES[idx % len(KARANA_NAMES)]
    return {"index": idx + 1, "name": name}


def get_tamil_month(dt_utc: datetime) -> dict:
    sun = _sun_sidereal_lon(dt_utc)
    month_idx = int(sun / 30.0) % 12
    day_in_month = int(sun % 30.0) + 1
    return {
        "month_index": month_idx + 1,
        "month_name": TAMIL_MONTHS[month_idx],
        "day": day_in_month,
        "display": f"{TAMIL_MONTHS[month_idx]} {day_in_month}",
    }


def find_next_tithi_boundary(start_utc: datetime, max_hours: int = 30) -> datetime:
    """Binary-search for exact moment the current tithi ends."""
    current_idx = tithi_at(start_utc).index
    step = timedelta(minutes=15)
    t1, t2 = start_utc, start_utc + step
    found = False
    for _ in range(int(max_hours * 60 / 15)):
        if tithi_at(t2).index != current_idx:
            found = True
            break
        t1 = t2
        t2 += step
    if not found:
        raise RuntimeError("Could not find next tithi boundary")
    left, right = t1, t2
    while (right - left).total_seconds() > 1:
        mid = left + (right - left) / 2
        if tithi_at(mid).index == current_idx:
            left = mid
        else:
            right = mid
    return right


def find_next_nakshatra_boundary(start_utc: datetime, max_hours: int = 48) -> datetime:
    """
    Binary-search for exact nakshatra boundary.
    Uses 10-minute steps for better accuracy, then narrows to 1 second.
    """
    current_idx = nakshatra_at(start_utc).index
    step = timedelta(minutes=10)
    t1, t2 = start_utc, start_utc + step
    found = False
    for _ in range(int(max_hours * 60 / 10)):
        if nakshatra_at(t2).index != current_idx:
            found = True
            break
        t1 = t2
        t2 += step
    if not found:
        raise RuntimeError("Could not find next nakshatra boundary")
    # Narrow down to within 1 second
    left, right = t1, t2
    while (right - left).total_seconds() > 1:
        mid = left + (right - left) / 2
        if nakshatra_at(mid).index == current_idx:
            left = mid
        else:
            right = mid
    return right


def get_day_tithi_segments_singapore(date_str: str) -> list[dict]:
    day_start_sg = datetime.fromisoformat(date_str).replace(tzinfo=SG_TZ)
    day_end_sg   = day_start_sg + timedelta(days=1)
    current_utc  = day_start_sg.astimezone(timezone.utc)
    end_utc      = day_end_sg.astimezone(timezone.utc)
    segments = []
    while current_utc < end_utc:
        info         = tithi_at(current_utc)
        boundary_utc = find_next_tithi_boundary(current_utc)
        seg_start_sg = current_utc.astimezone(SG_TZ)
        seg_end_sg   = min(boundary_utc, end_utc).astimezone(SG_TZ)
        segments.append({
            "tithi_index":      info.index + 1,
            "tithi_name":       info.name,
            "tithi_name_tamil": info.name_tamil,
            "paksha":           info.paksha,
            "start_sgt":        seg_start_sg.strftime("%H:%M"),
            "end_sgt":          seg_end_sg.strftime("%H:%M"),
            "start_sgt_iso":    seg_start_sg.isoformat(),
            "end_sgt_iso":      seg_end_sg.isoformat(),
        })
        current_utc = boundary_utc + timedelta(seconds=1)
    return segments
