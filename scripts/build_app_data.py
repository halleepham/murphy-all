"""Precompute what the first screen reads, from the 2025 replay (docs/decisions/0016). 2025 only.

Writes data/forecast/app/replay.duckdb: trips and their alternatives without outcomes, and the track
record, which is the one place outcomes are used. Uses hidden inputs (final_clean, 0014).
Usage: PYTHONPATH=. python scripts/build_app_data.py
"""
import duckdb, numpy as np, pandas as pd
from murphy.forecast.sample import ROOT
from murphy.forecast.score import PCOLS
from murphy.recommend import FIRM_FROM, UNSURE_FROM, made_it, p_make

R = ROOT / "data" / "forecast" / "alternatives" / "replay_final_clean"
F2025 = ROOT / "data" / "flights" / "2025_*.parquet"
OUT = ROOT / "data" / "forecast" / "app" / "replay.duckdb"
FARES = ROOT / "data" / "forecast" / "fares.parquet"
DEADLINES = (30, 60, 120)  # alternatives were saved for these only (0013)


def track_record() -> pd.DataFrame:
    c = pd.read_parquet(R / "current.parquet", columns=["outcome", "arr_delay_min", *PCOLS])
    rows = []
    for buf in DEADLINES:
        slack = np.full(len(c), buf)
        miss = 1 - p_make(c[PCOLS].fillna(0).to_numpy(), slack)
        missed = ~made_it(c.arr_delay_min, c.outcome, slack)
        band = np.select([miss < UNSURE_FROM, miss < FIRM_FROM], ["keep", "too_uncertain"], "high")
        for b in ("keep", "too_uncertain", "high"):
            k = band == b
            rows.append({"deadline_min": buf, "band": b, "forecasts": int(k.sum()),
                         "predicted_miss": float(miss[k].mean()), "true_miss": float(missed[k].mean())})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.unlink(missing_ok=True)
    cols = ", ".join(f"c.{k}" for k in PCOLS)
    alt_cols = ", ".join(f"a.{k}" for k in PCOLS)
    con = duckdb.connect(str(OUT))
    con.execute(f"""CREATE TABLE trips AS
        SELECT c.flight_id, c.lead_h, c.flight_date, c.as_of_utc, f.marketing_carrier AS carrier, f.flight_number,
               c.origin, c.dest, f.crs_dep_local, f.crs_arr_local,
               coalesce(f.cancelled AND f.dep_known_at < c.as_of_utc, false) AS known_cancelled, {cols}
        FROM read_parquet('{R}/current.parquet') c JOIN read_parquet('{F2025}') f USING (flight_id)
        ORDER BY c.flight_date, f.marketing_carrier, f.flight_number""")
    con.execute(f"""CREATE TABLE alts AS
        SELECT p.flight_id, p.lead_h, p.alt, p.alt_lead, p.arr_ahead_min, f.marketing_carrier AS carrier, f.flight_number,
               f.flight_date, f.crs_dep_local, f.crs_arr_local, {alt_cols}
        FROM read_parquet('{R}/pairs.parquet') p
        JOIN read_parquet('{R}/alt_forecasts.parquet') a ON a.alt = p.alt AND a.alt_lead = p.alt_lead
        JOIN read_parquet('{F2025}') f ON f.flight_id = p.alt
        ORDER BY p.flight_id, p.lead_h""")
    con.execute(f"CREATE TABLE fares AS SELECT * FROM read_parquet('{FARES}')")
    track = track_record()
    con.execute("CREATE TABLE track AS SELECT * FROM track")
    con.execute("CREATE INDEX trips_key ON trips (flight_id, lead_h)")
    con.execute("CREATE INDEX trips_find ON trips (flight_date, carrier, flight_number)")
    con.execute("CREATE INDEX alts_key ON alts (flight_id, lead_h)")
    print(con.execute("SELECT (SELECT count(*) FROM trips), (SELECT count(*) FROM alts), (SELECT count(*) FROM fares)").fetchall())
    print(track.round(4).to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
