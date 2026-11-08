"""The map's data (docs/decisions/0025). Code computes every number here; the page only draws.

Everything is as of the trip's forecast time: GCN scores for the hours up to that hour (never after),
weather known before it. No outcomes. Regions are shaded by the GCN, not by the day's flight
forecasts, because about half of a day's forecasts are made after the trip's (0025, Regions).
"""
import functools
from statistics import fmean

import pandas as pd

from murphy.forecast import rank
from murphy.forecast.sample import ROOT

HOURS_BACK = 24  # the slider runs from 24 h before the forecast hour up to it
LINKS = ROOT / "data" / "forecast" / "network" / "co_disrupts.parquet"  # scripts/export_links.py
COMMUNITIES = ROOT / "data" / "forecast" / "network" / "communities.csv"
AIRPORTS = ROOT / "data" / "airports.parquet"


@functools.cache
def inputs() -> dict | None:
    """The gitignored files the map reads, or None when any is missing on this machine."""
    s = rank.gcn_scores()
    if s is None or not (LINKS.exists() and AIRPORTS.exists()):
        return None
    cm = pd.read_csv(COMMUNITIES, keep_default_na=False)
    ap = pd.read_parquet(AIRPORTS, columns=["airport", "name", "lat", "lon"])
    return {"scores": s[0], "big": s[1], "places": cm.merge(ap, on="airport", how="left"),
            "links": pd.read_parquet(LINKS), "weather": weather_at}


def weather_at(airport: str, as_of) -> dict:
    """The latest observation and TAF known before as_of, as written. Limited outside the 30 airports."""
    from murphy.datalayer import asof
    from murphy.datalayer.weather import AIRPORTS as WX
    if airport not in WX:
        return {"airport": airport, "limited": True, "reason": f"No weather data for {airport}: murphy has it for 30 airports."}
    t = pd.Timestamp(as_of).tz_localize("UTC").to_pydatetime()
    obs, taf = asof.asos_as_of(t, airport, lookback_hours=3), asof.taf_as_of(t, airport)
    o = obs.iloc[-1] if len(obs) else None
    return {"airport": airport, "limited": False,
            "metar": None if o is None else {"text": o.metar, "obs_utc": str(o.obs_utc), "known_at": str(o.known_at)},
            "taf": None if taf.empty else {"issued_utc": str(taf.issued_utc.iloc[0]), "lines": taf.raw.tolist()},
            "source": "IEM ASOS and TAF archive, known before the forecast time (0007)"}


def build(origin: str, dest: str, as_of, scores, big: dict, places: pd.DataFrame, links: pd.DataFrame, weather) -> dict:
    h = rank.hour_index(as_of)
    rows = list(range(h - HOURS_BACK, h + 1))  # oldest first; the last is the forecast hour
    ok = [0 <= r < len(scores) for r in rows]
    gcn = {a: [float(scores[r, i]) if k else None for r, k in zip(rows, ok)] for a, i in big.items()}

    have = places.dropna(subset=["lat", "lon"])
    regions = []
    for c, g in places.groupby("community"):
        scored = [a for a in g.airport if a in gcn]
        regions.append({"community": int(c), "airports": len(g), "airports_scored": len(scored),
                        "risk": [fmean(v) if (v := [gcn[a][j] for a in scored if gcn[a][j] is not None]) else None
                                 for j in range(len(rows))]})

    if origin in big:
        nb = pd.concat([links[links.a == origin].rename(columns={"b": "airport"}),
                        links[links.b == origin].rename(columns={"a": "airport"})])
        nb = [{"airport": r.airport, "weight": float(r.weight), "gcn": gcn.get(r.airport)} for r in nb.itertuples()]
        nb.sort(key=lambda x: -x["weight"])  # the simpler baseline: link weight, as the `why` query retrieves today
        by_weight = [x["airport"] for x in nb[:rank.K]]
        # GCN order per hour; sorted is stable, so ties and blanks keep link-weight order
        by_gcn = [[x["airport"] for x in sorted(nb, key=lambda x: -x["gcn"][j] if x["gcn"] and x["gcn"][j] is not None
                                                 else float("inf"))[:rank.K]] for j in range(len(rows))]
        lk = {"limited": False, "neighbors": nb, "top_by_weight": by_weight, "top_by_gcn": by_gcn}
    else:
        lk = {"limited": True, "neighbors": [], "top_by_weight": [], "top_by_gcn": [],
              "reason": f"{origin} is not one of the 100 big airports the co-disruption links and GCN cover."}

    def place(a):
        p = places[places.airport == a]
        return None if p.empty or p.lat.isna().iloc[0] else {"airport": a, "name": p.name.iloc[0],
                                                           "lat": float(p.lat.iloc[0]), "lon": float(p.lon.iloc[0])}
    first = pd.Timestamp(rank.START)
    return {"route": {"origin": place(origin), "dest": place(dest)},
            "hours_utc": [str(first + pd.Timedelta(hours=r)) for r in rows],
            "airports": have[["airport", "name", "lat", "lon", "community", "big"]].assign(
                big=have.big.astype(str) == "True", community=have.community.astype(int)).to_dict("records"),
            "gcn": gcn, "regions": regions, "links": lk,
            "weather": {"origin": weather(origin, as_of), "dest": weather(dest, as_of)},
            "provenance": {"gcn": f"{rank.SCORES}, predicted late share of departures in the next 3 hours (0017, 0022)",
                           "regions": "co-disruption communities, 2023-24 (0017)",
                           "links": "CO_DISRUPTS, 2023-24, exported from Neo4j (0018, 0025)",
                           "forecast_as_of_utc": str(as_of), "forecast_hour_utc": str(first + pd.Timedelta(hours=h)),
                           "decisions": ["0025"]},
            "uncertainty": {"limits": [
                "Forecasts only, never what happened. The slider stops at the trip's forecast hour.",
                "Region shading uses the 100 big airports only.",
                f"Airports without coordinates are left off the map: {len(places) - len(have)}.",
                "Weather covers 30 airports."],
                "gcn_order": "On 2025 hours, the GCN's top 3 neighbors were among the 3 worst 45% of the time; "
                             "the top 3 by link weight 30%, about the same as random (0022 Finding 1)."}}
