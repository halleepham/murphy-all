"""Weather reports in plain words, by fixed rules (0025). No LLM: every word comes from a field.

A METAR row (data/weather/asos.parquet) and a TAF's periods (taf.parquet) become short sentences a
traveler can read, with times in the airport's local time. The raw text stays beside them as the
evidence. `notable` flags conditions by simple fixed thresholds, which are shown with the flags.
"""
import math
import re

import pandas as pd

from murphy.pastdays import DESCRIPTOR, INTENSITY, PHENOMENON, _list

SKY = {"FEW": "a few clouds", "SCT": "scattered clouds", "BKN": "broken clouds", "OVC": "overcast",
       "VV": "sky hidden, vertical visibility"}
CLEAR = {"CLR", "SKC", "NSC", "NCD"}
COMPASS = ["north", "north-northeast", "northeast", "east-northeast", "east", "east-southeast", "southeast",
           "south-southeast", "south", "south-southwest", "southwest", "west-southwest", "west",
           "west-northwest", "northwest", "north-northwest"]
OVER_6 = 6.01  # IEM stores "P6SM" (more than 6 statute miles) as 6.01
VRB = re.compile(r"\bVRB(\d{2,3})(?:G(\d{2,3}))?KT\b")  # the TAF parser leaves speed blank for variable wind
# murphy's own simple thresholds for "notable", not an aviation standard (AI choice, untested)
WIND_KT, GUST_KT, VIS_MI, CEILING_FT = 20, 30, 3, 1000
SERIOUS = {"TS": "thunderstorms", "SN": "snow", "FZ": "freezing rain or drizzle", "PL": "ice pellets",
           "FG": "fog", "GR": "hail"}
THRESHOLDS = (f"wind {WIND_KT} kt or more, gusts {GUST_KT} kt or more, visibility under {VIS_MI} miles, "
              f"broken or overcast clouds under {CEILING_FT:,} ft, or " + ", ".join(SERIOUS.values()))
NEAR_H = 1         # a forecast period counts for the flight if it overlaps the flight time +/- this
# Periods have no stored end, so the last runs to issue + span. Measured on 2025 TAFs: periods start up to
# ~30.7 h after issue at 29 of the 30 airports (30-hour TAFs), and at most 24.7 h at DAL (24-hour TAFs).
TAF_SPAN_H, TAF_SPAN_24H = 30, {"DAL"}


def _num(v):
    try:
        return None if v is None or pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return None


def local(ts, tz: str | None) -> str:
    t = pd.Timestamp(ts).tz_localize("UTC")
    return t.tz_convert(tz).strftime("%a %H:%M local") if tz else t.strftime("%a %H:%M UTC")


def phrase(code: str) -> str:
    """'-FZRAPL' -> 'light freezing rain and ice pellets'. Unknown letters are kept, never dropped."""
    words, c = [], code
    if c[:1] in INTENSITY:
        words.append(INTENSITY[c[0]]); c = c[1:]
    while c[:2] in DESCRIPTOR:
        words.append(DESCRIPTOR[c[:2]].removesuffix(" with").removesuffix(" of")); c = c[2:]
    things = []
    while c[:2] in PHENOMENON:
        things.append(PHENOMENON[c[:2]]); c = c[2:]
    if things:
        words.append(" and ".join(things))
    if c:
        words.append(c)
    return " ".join(words)


def wind(drct, sknt, gust, raw: str = "") -> str:
    s, g, d = _num(sknt), _num(gust), _num(drct)
    if s is None and (m := VRB.search(raw or "")):
        s, g, d = float(m.group(1)), _num(m.group(2)), None
    if s is None:
        return "wind not reported"
    if s == 0:
        return "calm wind"
    frm = "variable direction" if d is None else "from the " + COMPASS[round(d / 22.5) % 16]
    return f"wind {frm} at {s:.0f} kt" + (f", gusts to {g:.0f} kt" if g else "")


def visibility(v) -> str:
    v = _num(v)
    if v is None:
        return "visibility not reported"
    return "visibility over 6 miles" if v >= OVER_6 else f"visibility {v:g} mile{'' if v == 1 else 's'}"


def sky(codes, heights) -> str:
    layers = [(c, _num(h)) for c, h in zip(codes, list(heights) + [None] * len(codes)) if c]
    if not layers:
        return "sky not reported"
    if all(c in CLEAR for c, _ in layers):
        return "clear sky"
    return ", ".join(SKY.get(c, c) + (f" at {h:,.0f} ft" if h is not None else "") for c, h in layers if c not in CLEAR)


def sentence(parts: list[str]) -> str:
    text = "; ".join(p for p in parts if p)
    return text[:1].upper() + text[1:] + "."


def obs_text(r, tz) -> dict:
    """One METAR row -> {when, text} plus the fields `notable` reads."""
    codes = r.wxcodes.split() if isinstance(r.wxcodes, str) else []
    skyc = [c for c in (getattr(r, f"skyc{i}") for i in range(1, 5)) if isinstance(c, str)]
    skyl = [getattr(r, f"skyl{i}") for i in range(1, 5)]
    t = _num(r.tmpf)
    return {"when": f"Observed {local(r.obs_utc, tz)}",
            "text": sentence([", ".join(phrase(c) for c in codes), f"{t:.0f}°F" if t is not None else "",
                              wind(r.drct, r.sknt, r.gust), visibility(r.vsby), sky(skyc, skyl)]),
            "codes": codes, "skyc": skyc, "skyl": skyl, "sknt": _num(r.sknt), "gust": _num(r.gust), "vis": _num(r.vsby)}


def taf_lines(periods: pd.DataFrame, tz, around=None) -> list[dict]:
    """A TAF's periods -> [{when, text, near}] in order. `near`: the period overlaps `around` (UTC)
    +/- NEAR_H. A prevailing period (initial, FM) runs until the next one starts."""
    periods = periods.reset_index(drop=True)
    prev = periods.index[periods.period_type.isin(["initial", "FM"])].tolist()
    span = 24 if periods.airport.iloc[0] in TAF_SPAN_24H else TAF_SPAN_H
    stop = pd.Timestamp(periods.issued_utc.iloc[0]) + pd.Timedelta(hours=span)
    out = []
    for i, p in periods.iterrows():
        start = pd.Timestamp(p.period_start_utc)
        if i in prev:
            nxt = [j for j in prev if j > i]
            end = pd.Timestamp(periods.period_start_utc[nxt[0]]) if nxt else max(stop, start)
        else:
            end = pd.Timestamp(p.period_end_utc)
        s, e = local(start, tz), local(end, tz)
        when = {"TEMPO": f"At times, {s} to {e}", "PROB30": f"30% chance, {s} to {e}"}.get(p.period_type, f"From {s}")
        codes, skyc, skyl = _list(p.presentwx), _list(p.skyc), _list(p.skyl)
        full = i in prev  # TEMPO and PROB30 list only what changes
        parts = [", ".join(phrase(c) for c in codes),
                 wind(p.drct, p.sknt, p.gust, p.raw) if full or _num(p.sknt) is not None else "",
                 visibility(p.visibility) if full or _num(p.visibility) is not None else "",
                 sky(skyc, skyl) if full or skyc else ""]
        near = around is not None and start <= pd.Timestamp(around) + pd.Timedelta(hours=NEAR_H) \
            and end >= pd.Timestamp(around) - pd.Timedelta(hours=NEAR_H)
        out.append({"when": when, "text": sentence(parts), "near": bool(near), "codes": codes, "skyc": skyc,
                    "skyl": skyl, "sknt": _num(p.sknt), "gust": _num(p.gust), "vis": _num(p.visibility)})
    return out


def notable(items: list[dict]) -> list[str]:
    """Conditions past the thresholds above, in any of the items, each named once."""
    found = []
    def add(s):
        if s not in found:
            found.append(s)
    for x in items:
        if (x["sknt"] or 0) >= WIND_KT:
            add("strong wind")
        if (x["gust"] or 0) >= GUST_KT:
            add("strong gusts")
        if x["vis"] is not None and x["vis"] < VIS_MI:
            add("poor visibility")
        if any(c in ("BKN", "OVC", "VV") and _num(h) is not None and _num(h) < CEILING_FT
               for c, h in zip(x["skyc"], x["skyl"])):
            add("low clouds")
        for c in x["codes"]:
            body = c.lstrip("+-")
            for k in (body[i:i + 2] for i in range(0, len(body), 2)):  # two-letter groups, e.g. FZ RA
                if k in SERIOUS:
                    add(SERIOUS[k])
    return found
