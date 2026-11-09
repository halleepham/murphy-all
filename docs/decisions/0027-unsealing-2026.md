# 0027 — Unsealing 2026

Date: 9 Nov 2026. Branch `eval-2026`, from `about-page-and-firm60` at `81c7b70`.
**Written before any 2026 model result exists.** No 2026 forecast from a trained model has been
made. Nothing below has been run on 2026 yet.

## Human design

The owner decided on 9 Nov 2026 to open 2026 today and to run the evaluation in this session.
Forecast-only scoring comes first. The advice replay comes second, only if time allows. New scripts
and result files only: the app and the 2025 results do not change.

## What was locked

2026 is the test year (`0004`, `0010` Decision 6): January to August 2026, 479,815 sampled legs,
1,439,445 forecasts at 2, 6 and 24 h (`split == "test"` in `data/forecast/rows.parquet`).

Its outcomes were kept out of every choice:

- **Training:** every model fits on 2023–24 only (`gbm.load_split("fit")`).
- **Settings, rounds, cutoffs, inputs:** all chosen on 2025 (`0010`, `0013`, `0014`, `0017`).
- **Network inputs:** communities from 2023–24; GCNs trained on 2023–24; 2026 rows left blank
  (`scripts/network.py`).
- **Retrieval, graph, app:** similar days use 2023–25 (`murphy/pastdays.py`); the graph reads no
  2026 file (`scripts/build_graph.py`); the app runs on the 2025 replay.

**What touched 2026 before today, stated in full:**

1. **Climatology was scored on 2026 on 3 Nov** (`0008` Decision 5, committed): by-origin 0.6145,
   global 0.6172, uniform 0.9375. That was before any model was built. Climatology has two
   settings (365-day window, shrinkage 100 legs), both untuned. These numbers are public in the repo.
2. **2026 inputs were built** with the rest: groups A–E, and the hidden aircraft inputs (`0014`
   Decision 3, where 2026 flights lend to and borrow from only each other). Inputs, not outcomes.
3. **One early count of rows and airports** in `0017` included the 2026 files. No outcome.

So 2026 is clean for every model, cutoff and setting. It is not clean for climatology, which was
already seen on it.

## The frozen state

Commit `81c7b70`. Not merged into `main`, not pushed. Fixed from here:

| What | Frozen at | Source |
|---|---|---|
| App model | `final_network`, 300 rounds | `0017` Finding 4 |
| Network ablation | `final_clean`, 300 rounds | `0014` Finding 3 |
| Schedule-only model | `l2abl_a`, 50 rounds (its 2025 best) | `0010` Finding 2 |
| Schedule + history | `l2abl_ab`, its 2025 best round | `0010` Finding 2 |
| Climatology | by origin, global, uniform | `0008` |
| Advice rule | too uncertain 40–60%, firm from 60%, 15-point gain, at most 2 h earlier | `0014` Decision 4 |

## Why open it now

- The app is finished and every method in it was chosen on 2025. PLAN step 8 says to score 2026
  once after the freeze, and the freeze exists.
- 2025 is not pristine (`0010` Decision 6). Settings were picked on it, which flatters its scores.
  2026 is the only fair test of the forecast Murphy actually shows.
- The deliverables currently say "test 2025". `0010` calls 2025 *development*. A real 2026 result
  removes that overstatement.

## One step must come first: 2026 network inputs

`final_network` reads groups f (communities) and m (GCN, three seeds averaged). Both are blank for
every 2026 row. Scoring with blanks would test a broken input, not the model. Building them needs:

- **f:** the same windows as 2025, over the 2026 flight files, with the 2023–24 communities.
- **m:** the GCN weights were not saved, only their hourly predictions through 2025. The three
  co-disruption GCNs (seeds 0, 1, 2, trained on 2023–24) must be refit and run forward over 2026.
  **Check first:** the refit must reproduce the saved 2025 predictions. If it does not, stop and ask.

Neither reads a 2026 outcome. The model is not refit.

## What counts as good — set before seeing results

**AI proposal; owner accepted, 9 Nov 2026, before any 2026 result.** Each is pass or fail. 95% intervals resample whole
days, as on 2025. Absolute scores are expected to be worse in 2026, because climatology already is
(0.6145 against 0.6026), so the tests compare against climatology on the same flights.

| # | Test | Pass if | 2025 value |
|---|---|---|---|
| G1 | `final_network` minus by-origin climatology, multiclass Brier, all forecasts | interval entirely below 0 | about −0.042* |
| G2 | The same at each lead time, 2, 6 and 24 h | all three intervals below 0 | all below 0 |
| G3 | The gap holds up | 2026 gap at least half of the 2025 gap, recomputed by the same code | about −0.042* |
| G4 | `final_network` minus schedule-only (`l2abl_a`) | interval entirely below 0 | 0.5602 vs 0.5933 |
| G5 | Calibration, event "late": weighted mean gap | no worse than climatology's on 2026 | 2025: runs low in every bin |
| G6 | App bands at 60 min: true miss among "60% and up" | at least 60% | 82.0% |
| G7 | App bands at 60 min: true miss among "40 to 60%" | between 40% and 70% | 53.3% |

\*0.5602 − 0.6026, from two rounded figures. No paired interval was computed on 2025; the script computes it first.

**Reported, not pass or fail:**

- `final_network` minus `final_clean` (do network inputs help?). 2025: −0.0009, interval below 0.
  No claim of a gain unless the 2026 interval is also below 0.
- Late and cancelled Brier; by weather coverage; by aircraft kind (normal, overlap, no tail, delay
  blank), as in `0014`; predicted against true late share.
- **2025 January to August**, the same months as 2026, beside full 2025. Fall and holiday travel
  are not in 2026, so full-year 2025 is not a like-for-like comparison.

## Rules for the run

1. **One run.** Scripts are tested on 2025 first. On 2026 they run once, and those numbers are the result.
2. **No refit, no setting change, no new cutoff** after seeing 2026. A fix made after is reported as
   "changed after seeing 2026", never as tested on it.
3. **A failed test is reported** with the numbers and possible reasons. It is not explained away.
4. **New files only.** Code in `scripts/eval_2026.py`; results in `data/forecast/eval_2026/`
   (gitignored), with every figure copied into this record, as before.
5. **2025 is recomputed by the same code** and must reproduce the published 2025 figures
   (`final_network` 0.5602, `final_clean` 0.5612, climatology 0.6026). If it does not, stop.

## Advice replay — second, only if time allows

Same rule, same baselines as `0014` Finding 4: Murphy against the rule of thumb and the schedule-only
model, at 30, 60 and 120 minutes, net per 1,000. It needs alternatives built for 2026 trips (`0011`).
Its criteria will be written here before it runs.

## AI-recommendation instance

| AI recommended | Owner | Why |
|---|---|---|
| Build 2026 network inputs before scoring, with a reproduction check | accepted | Blank inputs would test a broken pipeline |
| Pass/fail tests G1–G7, relative to climatology | accepted | 2026 is harder for everyone; absolute scores would mislead |
| Also report 2025 Jan–Aug | accepted | 2026 has no fall or holidays |
