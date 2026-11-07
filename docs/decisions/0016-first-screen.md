# 0016 — The first screen

Date: 7 Nov 2026. Code: `murphy/app/`, `scripts/build_app_data.py`, `verdict` in `murphy/recommend.py`. Outputs (gitignored):
`data/forecast/app/replay.duckdb`. 2025 only; 2026 stays sealed. **Built, and plain on purpose: the owner will refine the design later.**

## Decision 1 — Build a thin screen before the required methods

**Human design:** the owner asked why an app came next when retrieval, GraphRAG and other required methods are not built.

**AI recommended, owner accepted, 6 Nov 2026:** the verdict and a plain screen first, then the methods in `docs/PLAN.md` order, because GraphRAG and the
explanations need a real recommendation to explain, and each method then has somewhere to appear. **Rejected:** verdict only (nothing to try until late); methods first (they would need the verdict anyway).

## What it does

FastAPI and one plain HTML page, both already approved (`0005`). No new dependency. The traveler picks a sampled 2025 flight, by date, airline and number or from examples
chosen by forecast alone.

| Required part | On the screen |
|---|---|
| Answer | Keep, too uncertain, consider changing, high risk with no clearly better flight, or known cancelled; and the chance of making the deadline |
| Evidence | Alternatives with chance, gain and estimated new ticket (`0015`) |
| Provenance | Model, forecast time, flight record, sources, decision records |
| Uncertainty | The track record for this risk band and deadline, and stated limits |
| Human controls | Forecast time, deadline, how much earlier the traveler could leave, sort by price |

**AI choices, for the owner to overrule:**

- A fifth verdict, "high risk, but no flight is clearly better". `0014` did not name this case.
- "Best" is shown only if the flight beats the current one. The first example had one alternative with a lower chance.
- Alternatives are hidden when the verdict is keep; they were saved only for risky trips.
- The deadline is 30, 60 or 120 minutes after scheduled arrival, not a clock time, because alternatives were saved for those only (`0013`). The traveler picks the forecast moment from 24, 6 or 2 h.
- No outcome is sent to the screen; only the track record uses outcomes. Showing what happened would make a useful demo control, but it is hindsight and is left out.

## Results

**Check:** every one of the 18,712 forecasts at 60% risk or more at a 60-minute deadline, run through the app's own code:

| Verdict | Forecasts | Share |
|---|---|---|
| Consider changing | 4,489 | 24.0% |
| High risk, no clearly better flight | 14,223 | 76.0% |

The 4,489 matches `0014` Decision 4 exactly. **Read:** on about three of four high-risk forecasts murphy warns but has nothing clearly better to offer. Each took 18 ms, reading the data file directly.

**Track record shown** (all of 2025, all lead times):

| Deadline | Band | Forecasts | Predicted miss | True miss |
|---|---|---|---|---|
| 30 min | Under 40% | 1,934,685 | 12.2% | 13.2% |
| 30 min | 40% to 60% | 88,189 | 48.2% | 52.1% |
| 30 min | 60% and up | 47,579 | 75.5% | 81.7% |
| 60 min | Under 40% | 2,016,640 | 7.7% | 8.5% |
| 60 min | 40% to 60% | 35,101 | 48.0% | 53.6% |
| 60 min | 60% and up | 18,712 | 74.4% | 82.3% |
| 120 min | Under 40% | 2,052,080 | 4.2% | 4.7% |
| 120 min | 40% to 60% | 12,678 | 48.1% | 54.5% |
| 120 min | 60% and up | 5,695 | 72.3% | 80.2% |

## Limits

- 2025 settings were chosen on these results, so the track record is not independent.
- Forecasts exist for sampled flights only, so most flights a traveler types return nothing.
- The moment is chosen directly. Replaying a clock time, using the latest moment at or before it (`0013` Decision 2), is not built.
- Itinerary text, connections, explanations and the map are later layers. Nothing here uses an LLM.
- The check above is on the code path, not the browser. The page was looked at for one flight, by headless Chrome screenshot.
- **The "known cancelled" verdict never fires on the replay:** 0 of 2,070,453 forecasts, though 32,313 are on flights that were cancelled. BTS does not record when a cancellation was announced, so
  `murphy/datalayer/bts.py` treats it as known at scheduled departure (all 113,966 cancelled 2025 flights), and every forecast is made before that. The check required by `0013` Decision 2 exists and is tested, but only on made-up data. The same applies to the
  alternatives filter in `0013`, which therefore removes nothing: a replay may offer a flight the airline had already canceled.
- Port 8000 is held by a Docker service on this machine, so the app runs on 8765.

## Tests

`tests/test_app.py` and `test_verdict` in `tests/test_recommend.py`: each verdict at its edges; best marked and cost traced; the earlier limit; price sort that never changes the advice; a worse flight never best; known cancelled; high risk with nothing to offer (the thin-evidence case); unknown flight and bad settings refused; no outcome in a response. The simpler comparison stays the rule of thumb (`0014`).
