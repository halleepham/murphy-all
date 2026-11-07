"""The first screen's API: one precomputed 2025 trip and its advice (docs/decisions/0016).

Numbers come from code here. No outcome is ever returned for a trip, so the screen cannot show
hindsight; the track record is the only figure built from outcomes.
"""
from pathlib import Path

import duckdb
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from murphy.cost import estimated_fare
from murphy.forecast.sample import ROOT
from murphy.forecast.score import PCOLS
from murphy.recommend import FIRM_FROM, MAX_EARLIER_H, UNSURE_FROM, p_make, verdict

DB = ROOT / "data" / "forecast" / "app" / "replay.duckdb"
LEADS = {24, 6, 2}
DEADLINES = {30, 60, 120}
STATIC = Path(__file__).parent / "static"
LIMITS = [
    "Replay of 2025 only. Forecasts exist for sampled flights at 24, 6 and 2 hours before departure.",
    "Murphy can rarely warn about flights later swapped or cancelled.",
    "Past schedules show that a flight existed, not that it had a seat.",
    "Estimated costs are what people typically paid, not a quote. A last-minute seat may cost more.",
]


def advice(con, flight_id: str, lead_h: int, deadline_min: int, max_earlier_h: float, sort: str = "chance") -> dict | None:
    cols = ", ".join(PCOLS)
    t = con.execute(f"SELECT flight_id, lead_h, flight_date, as_of_utc, carrier, flight_number, origin, dest, crs_dep_local, "
                    f"crs_arr_local, known_cancelled, {cols} FROM trips WHERE flight_id = ? AND lead_h = ?",
                    [flight_id, lead_h]).df()
    if t.empty:
        return None
    t = t.iloc[0]
    current = float(p_make(t[PCOLS].fillna(0).to_numpy(dtype=float)[None], [deadline_min])[0])
    a = con.execute(f"SELECT alt, alt_lead, arr_ahead_min, carrier, flight_number, flight_date, crs_dep_local, crs_arr_local, {cols} "
                    "FROM alts WHERE flight_id = ? AND lead_h = ? AND arr_ahead_min + ? >= 0 AND alt_lead - lead_h >= ?",
                    [flight_id, lead_h, deadline_min, -max_earlier_h]).df()
    fares = con.execute("SELECT * FROM fares WHERE origin = ? AND dest = ?", [t.origin, t.dest]).df()
    alts = []
    if len(a):
        a["chance"] = p_make(a[PCOLS].fillna(0).to_numpy(dtype=float), (a.arr_ahead_min + deadline_min).to_numpy())
        a = a.sort_values("chance", ascending=False, kind="stable")
        for i, (_, r) in enumerate(a.iterrows()):
            alts.append({"flight": f"{r.carrier} {r.flight_number}", "flight_id": r.alt, "date": str(r.flight_date)[:10],
                         "departs_local": r.crs_dep_local, "arrives_local": r.crs_arr_local,
                         "chance": float(r.chance), "gain": float(r.chance - current), "best": i == 0 and r.chance > current,  # never mark a worse flight as best
                         "same_airline": r.carrier == t.carrier,
                         "cost": estimated_fare(fares, t.origin, t.dest, r.carrier)})
    best = alts[0]["chance"] if alts else None
    if sort == "price":  # no estimate goes last; ties keep the order by chance
        alts.sort(key=lambda x: (x["cost"]["fare"] is None, x["cost"]["fare"] or 0))
    v = verdict(current, best, bool(t.known_cancelled))
    band = "keep" if 1 - current < UNSURE_FROM else "too_uncertain" if 1 - current < FIRM_FROM else "high"
    track = con.execute("SELECT forecasts, predicted_miss, true_miss FROM track WHERE deadline_min = ? AND band = ?",
                        [deadline_min, band]).df().iloc[0]
    return {"answer": {"verdict": v, "chance": current, "miss": 1 - current},
            "flight": {"flight": f"{t.carrier} {t.flight_number}", "flight_id": t.flight_id, "date": str(t.flight_date)[:10],
                       "origin": t.origin, "dest": t.dest, "departs_local": t.crs_dep_local, "arrives_local": t.crs_arr_local},
            "alternatives": alts,
            "provenance": {"model": "final_clean", "forecast_as_of_utc": str(t.as_of_utc), "lead_h": int(t.lead_h),
                           "data": "BTS On-Time Performance 2025; IEM weather", "decisions": ["0014", "0015", "0016"]},
            "uncertainty": {"track_record": {"band": band, "forecasts": int(track.forecasts),
                                             "predicted_miss": float(track.predicted_miss), "true_miss": float(track.true_miss)},
                            "limits": LIMITS}}


def create_app(db: Path = DB) -> FastAPI:
    app = FastAPI(title="murphy")
    con = duckdb.connect(str(db), read_only=True)

    @app.get("/")
    def page():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/flights")
    def flights(date: str, carrier: str, number: int):
        rows = con.cursor().execute(
            "SELECT DISTINCT flight_id, origin, dest, crs_dep_local FROM trips WHERE flight_date = TRY_CAST(? AS DATE) "
            "AND carrier = ? AND flight_number = ? ORDER BY crs_dep_local", [date, carrier.strip().upper(), number]).df()
        return rows.to_dict("records")

    @app.get("/api/examples")
    def examples():
        """Picked by forecast alone: flights with a high risk at 2 h and a 60-minute deadline."""
        miss = " + ".join(f"coalesce({k}, 0)" for k in PCOLS[:5])
        rows = con.cursor().execute(
            f"SELECT flight_id, carrier || ' ' || flight_number AS flight, origin, dest, flight_date::VARCHAR AS date FROM trips "
            f"WHERE lead_h = 2 AND flight_id IN (SELECT DISTINCT flight_id FROM alts WHERE lead_h = 2) AND 1 - ({miss}) >= ? "
            "ORDER BY md5(flight_id) LIMIT 6", [FIRM_FROM]).df()
        return rows.to_dict("records")

    @app.get("/api/trip")
    def trip(flight_id: str, lead_h: int = 2, deadline_min: int = 60,
             max_earlier_h: float = Query(MAX_EARLIER_H, ge=0, le=24), sort: str = Query("chance", pattern="^(chance|price)$")):
        if lead_h not in LEADS or deadline_min not in DEADLINES:
            raise HTTPException(422, f"lead_h must be one of {sorted(LEADS)}, deadline_min one of {sorted(DEADLINES)}")
        got = advice(con.cursor(), flight_id, lead_h, deadline_min, max_earlier_h, sort)
        if got is None:
            raise HTTPException(404, "No forecast for this flight at this time. Forecasts cover sampled 2025 flights only.")
        return got

    return app
