# 0024 — The deadline what-if chart (PLAN layer 6, "a presentation beyond a static chart")

Date: 8 Nov 2026. 2025 only; no 2026 outcome was read. **Built.**
Code: `scripts/deadline_check.py` (the band at every step), `typical` and the wider track record in
`scripts/build_app_data.py`, `curve` in `advice` in `murphy/app/server.py`, the chart in
`murphy/app/static/trip.html`. Tests: the curve tests in `tests/test_app.py`.
Results (gitignored): `data/forecast/alternatives/replay_final_network/deadline_band.csv`;
logs `data/forecast/logs/deadline_check.log`, `build_app_data.log`.

## Human design

The owner wants at least one interactive chart, and the traveler should be able to change the
deadline (PLAN layer 7 human control).

## AI recommendation and the owner's decision

The forecast is a spread of arrival delay in 15-minute steps to 3 hours (`EDGES`), so the chance
can be computed at any 15-minute deadline with the existing `p_make`; only the app's allowed list
(30, 60, 120) stood in the way. The track record and the 40/60% band had been checked only at those
three. Options offered: (A) snap to 30/60/120; (B) any step, labeled "not checked"; (C) any step,
checked first. The AI found the saved alternatives reach only 120 minutes past the original's
arrival (`pairs.parquet`, min `arr_ahead_min` = −120), so going past 120 would need the
alternatives rebuilt (about 23 min in `0013`).

**AI recommended C up to 120 minutes; owner accepted, 8 Nov 2026.**

## Decisions

1. **Deadlines 0 to 120 minutes in 15-minute steps**, each with its own track record. The chart
   draws the forecast's full range to 180, shaded "not checked" past 120; the deadline cannot be
   set there.
2. **Three lines:** this flight; the best alternative at the chosen deadline (only when one is
   better); the typical 2025 flight at the same lead time (the mean of `p_make` over all 2,070,453
   replayed forecasts), the simpler comparison.
3. **Click or drag on the chart** sets the deadline; the advice reloads when the pointer is
   released. The deadline dropdown stays as the keyboard control.
4. **The page computes nothing.** Every point comes from the server's `p_make`. Steps hold each
   value until the next step, as `p_make` does (a deadline of 70 min gets the 60-min chance).
5. **Ask stays at 60 minutes** (`0019`).

## Finding — the band holds at every step

Same tally as `0014` Decision 4 (the change that would be offered in each risk range, at the
same gain), lead times together. Run time 33 s; it reproduces the saved 30/60/120 rows of
`band.csv` exactly. Rescued and needless are counts of trips:

| Deadline | 40–50%: rescued / needless | 50–60%: rescued / needless | 60%+: rescued / needless |
|---|---|---|---|
| 0 | 55 / 62 | 2,961 / 2,464 | 38,492 / 14,637 |
| 15 | 10,380 / 13,005 | 9,154 / 8,058 | 13,831 / 5,042 |
| 30 | 6,730 / 8,809 | 4,219 / 3,675 | 6,319 / 1,940 |
| 45 | 3,638 / 4,676 | 2,072 / 1,894 | 3,653 / 985 |
| 60 | 2,101 / 2,701 | 1,171 / 1,084 | 2,503 / 660 |
| 75 | 1,247 / 1,733 | 884 / 754 | 1,787 / 517 |
| 90 | 853 / 1,288 | 703 / 600 | 1,211 / 401 |
| 105 | 686 / 1,005 | 523 / 473 | 853 / 290 |
| 120 | 545 / 780 | 419 / 340 | 632 / 248 |

At every step the pattern behind `0014` Decision 4 repeats: below 50% a change is needless more
often than it rescues; from 50 to 60% the two are close (rescued/needless 1.08 to 1.23, against
1.08 at 60 minutes, where the band was set); from 60% a change rescues 2.5 to 3.8 times as often as
it is needless. **So the band is kept unchanged at every deadline.**

Not hidden: forecasts in the 60%+ band under-predict missing at every deadline (true miss 0.76 to
0.82 against predicted 0.72 to 0.76), the same gap already shown at 30/60/120. The track record on
the page states it.

## Evidence

- `deadline_check.py`: "reproduces band.csv: True"; 33 s, 3.0 GB peak.
- `build_app_data.py` rebuilt in 16 s: 2,070,453 trips, 776,125 alternatives (as in `0017`); the
  60-minute track record matches `0017` (7.8/8.5%, 48.0/53.3%, 74.5/82.0%).
- `pytest -q`: 199 passed. New tests: every step 0–120 is accepted; 50 and 135 are refused (the
  deliberate failure cases); the curve never falls and equals the chance at each deadline; the
  best-alternative and typical lines; no best-alternative line when nothing is better.
- Headless Chrome screenshot of the example flight (F9 4195 LGA→MIA, 9 Jan 2025): at +60 min the
  chart shows 19%, the same as the card; best alternative AA 3297 at 71%; typical flight 91%.
- Not checked by a test: the drag itself (pointer events in a real browser).
