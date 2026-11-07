import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from murphy.app.server import create_app
from murphy.forecast.score import PCOLS


def probs(make):
    """Chance `make` of arriving within 15 minutes, the rest after three hours."""
    return {k: 0.0 for k in PCOLS} | {"p_0_15": make, "p_180p": 1 - make}


def trip(fid, make, cancelled=False):
    return {"flight_id": fid, "lead_h": 2, "flight_date": "2025-03-01", "as_of_utc": "2025-03-01 10:00:00", "carrier": "DL",
            "flight_number": 1, "origin": "LGA", "dest": "ORD", "crs_dep_local": "0700", "crs_arr_local": "0900",
            "known_cancelled": cancelled, **probs(make)}


def alt(fid, aid, make, carrier, earlier_h=0.0):
    return {"flight_id": fid, "lead_h": 2, "alt": aid, "alt_lead": 2 - earlier_h, "arr_ahead_min": 0, "carrier": carrier,
            "flight_number": 9, "flight_date": "2025-03-01", "crs_dep_local": "0800", "crs_arr_local": "1000", **probs(make)}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    path = tmp_path_factory.mktemp("app") / "t.duckdb"
    con = duckdb.connect(str(path))
    trips = pd.DataFrame([trip("low", .9), trip("mid", .5), trip("high", .2), trip("gone", .2, True), trip("alone", .2), trip("low2", .9)])
    alts = pd.DataFrame([alt("high", "a1", .9, "UA"), alt("high", "a2", .8, "DL"), alt("high", "a3", .7, "XX"),
                         alt("high", "a4", .95, "UA", earlier_h=3), alt("mid", "a5", .9, "UA"), alt("low2", "a6", .5, "UA")])
    fares = pd.DataFrame({"origin": ["LGA", "LGA"], "dest": ["ORD", "ORD"], "carrier": ["UA", "DL"], "tickets": [100, 100], "fare": [300.0, 200.0]})
    track = pd.DataFrame([{"deadline_min": 60, "band": b, "forecasts": 10, "predicted_miss": .5, "true_miss": .6} for b in ("keep", "too_uncertain", "high")])
    for name in ("trips", "alts", "fares", "track"):
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM {name}")
    con.close()
    return TestClient(create_app(path))


def get(client, fid, **kw):
    return client.get("/api/trip", params={"flight_id": fid, **kw})


def test_low_risk_keeps(client):
    assert get(client, "low").json()["answer"]["verdict"] == "keep"


def test_high_risk_changes_marks_best_and_traces_the_cost(client):
    d = get(client, "high").json()
    assert d["answer"]["verdict"] == "consider_changing"
    assert [(a["flight_id"], a["best"]) for a in d["alternatives"]] == [("a1", True), ("a2", False), ("a3", False)]
    assert d["alternatives"][0]["cost"]["fare"] == 300.0 and "DB1B" in d["alternatives"][0]["cost"]["source"]
    assert d["provenance"]["model"] == "final_clean" and d["uncertainty"]["limits"]


def test_too_uncertain_still_lists_alternatives(client):
    d = get(client, "mid").json()
    assert d["answer"]["verdict"] == "too_uncertain" and len(d["alternatives"]) == 1


def test_earlier_limit_is_the_travelers_control(client):
    assert get(client, "high", max_earlier_h=3).json()["alternatives"][0]["flight_id"] == "a4"


def test_price_sort_reorders_but_cost_never_changes_the_advice(client):
    by_chance, by_price = get(client, "high").json(), get(client, "high", sort="price").json()
    assert [a["flight_id"] for a in by_price["alternatives"]] == ["a2", "a1", "a3"]  # no estimate last
    assert by_price["alternatives"][2]["cost"]["fare"] is None
    assert [a["flight_id"] for a in by_price["alternatives"] if a["best"]] == ["a1"]
    assert by_price["answer"] == by_chance["answer"]


def test_a_worse_flight_is_never_marked_best(client):
    d = get(client, "mid", deadline_min=60).json()
    assert d["alternatives"][0]["best"] is True  # 90% against 50%
    assert all(not a["best"] for a in get(client, "low2").json()["alternatives"])


def test_known_cancelled_is_stated(client):
    assert get(client, "gone").json()["answer"]["verdict"] == "cancelled"


def test_high_risk_with_nothing_to_offer(client):
    d = get(client, "alone").json()
    assert d["answer"]["verdict"] == "at_risk_no_better_flight" and d["alternatives"] == []


def test_unknown_flight_and_bad_settings_are_refused(client):
    assert get(client, "nope").status_code == 404
    assert get(client, "low", deadline_min=45).status_code == 422
    assert get(client, "low", sort="vibes").status_code == 422


def test_no_outcome_reaches_the_screen(client):
    text = get(client, "high").text
    assert "outcome" not in text and "arr_delay" not in text


def test_find_a_flight(client):
    rows = client.get("/api/flights", params={"date": "2025-03-01", "carrier": "dl", "number": 1}).json()
    assert len(rows) == 6
    assert client.get("/api/flights", params={"date": "not-a-date", "carrier": "DL", "number": 1}).json() == []
