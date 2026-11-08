"""Would one-stop connections add alternatives? A schedule-and-hindsight check, not a model result.

For each replay forecast in the 0018 window (4-12 Jan 2025), with a deadline DEADLINE_MIN after
the trip's scheduled arrival:
  direct      same route, any carrier: the 0013 rule (leaves 1-24 h after as_of, arrives by
              the deadline, not known cancelled at as_of)
  connection  same marketing carrier on both legs, through any hub: leg 1 leaves 1-24 h after
              as_of, leg 2 leaves at least MCT after leg 1's scheduled arrival and is scheduled
              to arrive by the deadline; neither leg known cancelled at as_of
Hindsight, for an upper bound only: an option "worked" if it actually arrived by the deadline,
and for a connection, leg 1 actually landed at least MCT before leg 2 actually left. Seats are
unknown, so this overstates what a traveler could have booked.

Usage: PYTHONPATH=. python scripts/connections_check.py [mct_min ...]
"""
import sys, time
import duckdb
from murphy.graph import ROOT

WINDOW = ("2025-01-04", "2025-01-12")
LEGS = ROOT / "data" / "flights" / "2025_01.parquet"
APP = ROOT / "data" / "forecast" / "app" / "replay.duckdb"
DEADLINE_MIN = 60
OK = "NOT f.cancelled AND NOT f.diverted"  # ends up arriving


def run(con, mct: int):
    con.execute(f"""CREATE OR REPLACE TEMP TABLE opt AS
    WITH d AS (  -- direct alternatives
      SELECT t.flight_id, t.lead_h, count(*) n,
             bool_or(NOT a.cancelled AND NOT a.diverted AND a.actual_arr_utc <= t.deadline) worked
      FROM t JOIN legs a ON a.origin = t.origin AND a.dest = t.dest AND a.flight_id <> t.flight_id
       AND a.sched_dep_utc BETWEEN t.as_of_utc + INTERVAL 1 HOUR AND t.as_of_utc + INTERVAL 24 HOUR
       AND a.sched_arr_utc <= t.deadline AND NOT (a.cancelled AND a.dep_known_at < t.as_of_utc)
      GROUP BY 1, 2),
    c AS (  -- one-stop connections, same marketing carrier
      SELECT t.flight_id, t.lead_h, count(*) n, count(DISTINCT l1.dest) hubs,
             bool_or(NOT l1.cancelled AND NOT l1.diverted AND NOT l2.cancelled AND NOT l2.diverted
                     AND l1.actual_arr_utc + to_minutes({mct}) <= l2.actual_dep_utc
                     AND l2.actual_arr_utc <= t.deadline) worked
      FROM t JOIN legs l1 ON l1.origin = t.origin AND l1.dest <> t.dest AND l1.marketing_carrier = t.carrier
       AND l1.sched_dep_utc BETWEEN t.as_of_utc + INTERVAL 1 HOUR AND t.as_of_utc + INTERVAL 24 HOUR
       AND NOT (l1.cancelled AND l1.dep_known_at < t.as_of_utc)
      JOIN legs l2 ON l2.origin = l1.dest AND l2.dest = t.dest AND l2.marketing_carrier = t.carrier
       AND l2.sched_dep_utc >= l1.sched_arr_utc + to_minutes({mct}) AND l2.sched_arr_utc <= t.deadline
       AND NOT (l2.cancelled AND l2.dep_known_at < t.as_of_utc)
      GROUP BY 1, 2)
    SELECT t.flight_id, t.lead_h, t.day, t.made_it, coalesce(d.n, 0) n_direct, coalesce(d.worked, false) direct_worked,
           coalesce(c.n, 0) n_conn, coalesce(c.hubs, 0) hubs, coalesce(c.worked, false) conn_worked
    FROM t LEFT JOIN d USING (flight_id, lead_h) LEFT JOIN c USING (flight_id, lead_h)""")
    s = con.sql("""SELECT count(*) forecasts,
        round(avg((n_direct > 0)::int), 3) has_direct, round(avg((n_conn > 0)::int), 3) has_conn,
        round(avg((n_conn > 0 AND n_direct = 0)::int), 3) conn_only,
        round(median(n_conn) FILTER (WHERE n_conn > 0), 1) median_conn, round(median(hubs) FILTER (WHERE n_conn > 0), 1) median_hubs,
        sum((NOT made_it)::int) trip_missed,
        sum((NOT made_it AND direct_worked)::int) missed_direct_worked,
        sum((NOT made_it AND conn_worked)::int) missed_conn_worked,
        sum((NOT made_it AND conn_worked AND NOT direct_worked)::int) missed_only_conn_worked
        FROM opt""").df()
    print(f"\nMCT {mct} min\n" + s.T.to_string(header=False), flush=True)
    return s


def main(mcts):
    t0 = time.time()
    con = duckdb.connect()
    con.execute(f"ATTACH '{APP}' AS app (READ_ONLY)")
    con.execute(f"CREATE TEMP TABLE legs AS SELECT * FROM read_parquet('{LEGS}')")
    con.execute(f"""CREATE TEMP TABLE t AS
      SELECT r.flight_id, r.lead_h, r.as_of_utc, r.carrier, r.origin, r.dest, r.flight_date::DATE AS day,
             f.sched_arr_utc + to_minutes({DEADLINE_MIN}) deadline,
             ({OK} AND f.arr_delay_min < {DEADLINE_MIN}) made_it
      FROM app.trips r JOIN legs f USING (flight_id)
      WHERE r.flight_date BETWEEN '{WINDOW[0]}' AND '{WINDOW[1]}'""")
    print("forecasts", con.sql("SELECT count(*), count(DISTINCT flight_id) FROM t").fetchall(), flush=True)
    for m in mcts:
        run(con, m)
    run(con, 45)  # last, so the by-day table below is at 45
    print("\nBy day, MCT 45, forecasts where the trip missed:")
    print(con.sql("""SELECT day, count(*) FILTER (WHERE NOT made_it) missed,
        sum((NOT made_it AND direct_worked)::int) direct_worked, sum((NOT made_it AND conn_worked)::int) conn_worked,
        sum((NOT made_it AND conn_worked AND NOT direct_worked)::int) only_conn
        FROM opt GROUP BY 1 ORDER BY 1""").df().to_string(index=False))
    print(f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or [30, 60])
