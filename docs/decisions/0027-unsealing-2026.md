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

## Finding 1 — The 2026 forecast test, 9 Nov 2026

**Run once.** Commands, all `PYTHONPATH=. python scripts/eval_2026.py`, logs in `data/forecast/logs/eval_2026_*.log`:

1. `inputs`: three GCNs refit (175, 157, 156 s). They reproduce the saved 2025 average exactly (largest difference
   0.0), except the last 2 hours of 31 Dec 2025, which now see the 1 Jan schedule; saved 2025 inputs are kept, so
   nothing changes there. 2026 rows with a blank GCN input: 9.8%, against 9.3% in 2025.
2. `score tune`: reproduced 0.5602, 0.5612, 0.6026 and the 60-minute bands 82.0%, 53.3%, 8.5%.
3. `score test`: 1,439,445 forecasts.
4. `compare`. Its first run stopped at a printing bug (`log` took no `sep`), after the scores were written; fixed
   and rerun. The fix changes no computed value.

**All seven tests pass.**

| # | Test | 2026 | 2025 | Result |
|---|---|---|---|---|
| G1 | `final_network` minus by-origin climatology | −0.0486 (−0.0531 to −0.0446) | −0.0424 (−0.0446 to −0.0402) | pass |
| G2 | The same at 2, 6, 24 h | −0.0729, −0.0415, −0.0314, all below 0 | −0.0658, −0.0355, −0.0258 | pass |
| G3 | At least half of 2025's gap (−0.0212) | −0.0486 | | pass |
| G4 | Minus schedule-only | −0.0366 (−0.0416 to −0.0326) | −0.0331 | pass |
| G5 | Late calibration gap, against climatology | 0.0053 against 0.0126 | 0.0112 against 0.0157 | pass |
| G6 | "60% and up" true miss, 60 min | 81.8% (predicted 74.8%) | 82.0% | pass |
| G7 | "40 to 60%" true miss, 60 min | 52.7% (predicted 48.4%) | 53.3% | pass |

**Multiclass Brier, all forecasts.** Lower is better.

| Model | 2026 | 2025 | 2025 Jan–Aug |
|---|---|---|---|
| uniform | 0.9375 | 0.9375 | 0.9375 |
| climatology, global | 0.6172 | 0.6043 | 0.6140 |
| climatology, by origin | 0.6145 | 0.6026 | 0.6120 |
| schedule only (`l2abl_a`) | 0.6024 | 0.5933 | 0.6005 |
| schedule + history (`l2abl_ab`) | 0.5982 | 0.5900 | 0.5970 |
| `final_clean` | 0.5666 | 0.5612 | 0.5682 |
| **`final_network`** | **0.5659** | **0.5602** | **0.5676** |

**Late and cancelled Brier.**

| Model | Late 2026 | Late 2025 | Late 2025 Jan–Aug | Cancelled 2026 | Cancelled 2025 | Cancelled 2025 Jan–Aug |
|---|---|---|---|---|---|---|
| climatology, by origin | 0.1870 | 0.1793 | 0.1837 | 0.0219 | 0.0153 | 0.0165 |
| schedule only | 0.1791 | 0.1733 | 0.1752 | 0.0219 | 0.0153 | 0.0165 |
| `final_clean` | 0.1525 | 0.1485 | 0.1504 | 0.0173 | 0.0134 | 0.0142 |
| `final_network` | 0.1522 | 0.1479 | 0.1500 | 0.0171 | 0.0133 | 0.0142 |

**Differences, multiclass Brier, 95% interval by day.**

| Comparison | 2026 | 2025 | 2025 Jan–Aug |
|---|---|---|---|
| `final_network` − climatology | −0.0486 (−0.0531 to −0.0446) | −0.0424 (−0.0446 to −0.0402) | −0.0444 (−0.0471 to −0.0416) |
| `final_network` − schedule only | −0.0366 (−0.0416 to −0.0326) | −0.0331 (−0.0352 to −0.0310) | −0.0329 (−0.0350 to −0.0309) |
| `final_network` − schedule + history | −0.0323 (−0.0369 to −0.0284) | −0.0297 (−0.0317 to −0.0278) | −0.0294 (−0.0314 to −0.0275) |
| `final_network` − `final_clean` (network inputs) | −0.00072 (−0.00101 to −0.00050) | −0.00093 (−0.00111 to −0.00077) | −0.00061 (−0.00074 to −0.00046) |
| schedule only − climatology | −0.0121 (−0.0136 to −0.0104) | −0.0093 (−0.0108 to −0.0076) | −0.0115 (−0.0135 to −0.0095) |

**Calibration, event "late", weighted mean gap:** `final_network` 0.0053 (2026), 0.0112 (2025), 0.0060 (2025 Jan–Aug);
climatology 0.0126, 0.0157, 0.0258. In 2026 it still runs low above 20%, by 0.005 to 0.031 a bin; predicted late
share 24.7% against 25.1% true.

**The app's bands, `final_network`, true miss (predicted).**

| Deadline | Band | 2026 | 2025 | 2025 Jan–Aug |
|---|---|---|---|---|
| 30 min | keep | 13.6% (13.4%) | 13.0% (12.3%) | 13.3% (13.2%) |
| 30 min | too uncertain | 49.7% (48.2%) | 51.6% (48.2%) | 50.4% (48.1%) |
| 30 min | 60% and up | 80.6% (76.1%) | 81.4% (75.7%) | 80.4% (75.4%) |
| 60 min | keep | 8.9% (8.7%) | 8.5% (7.8%) | 8.8% (8.6%) |
| 60 min | too uncertain | 52.7% (48.4%) | 53.3% (48.0%) | 51.7% (47.9%) |
| 60 min | 60% and up | 81.8% (74.8%) | 82.0% (74.5%) | 80.9% (74.3%) |
| 120 min | keep | 5.1% (4.8%) | 4.6% (4.2%) | 4.9% (4.7%) |
| 120 min | too uncertain | 55.9% (48.6%) | 54.1% (48.2%) | 52.5% (48.2%) |
| 120 min | 60% and up | 81.3% (73.4%) | 79.8% (72.4%) | 78.7% (72.5%) |

2026 forecasts at 60 min: 1,383,828 keep, 33,432 too uncertain, 22,185 at 60% and up.

**By aircraft inputs as recorded, under 24 h, multiclass Brier** (`final_network` / climatology): normal 0.5423 /
0.5935 (922,058); overlap 1.0813 / 1.1777 (22,416); delay blank 0.6551 / 0.9717 (11,604); no tail 0.7989 / 1.3375
(3,552). As on 2025, hidden flights score far worse than normal ones.

**Read:**
- The forecast holds up on a year it never saw. Its lead over climatology is about the same as on 2025, and a
  little larger (−0.0486 against −0.0424, or −0.0444 for the same months of 2025). The intervals overlap.
- 2026 is harder for every model. All absolute scores are worse than 2025's, close to 2025 Jan–Aug, so most of
  the gap is season, not drift. Cancellations are higher in 2026 (Brier 0.0219 against 0.0165 for climatology).
- Network inputs still help a little: −0.0007, interval below 0, about the size seen on 2025.
- The bands mean what the app says they mean. "60% and up" misses about 81% of the time in every column.
  The forecast still runs low on risky flights, as on 2025.
- Not tested here: the advice replay (net per 1,000 against the rule of thumb). Fall and holiday travel.

**Limits:** one year of eight months, the same 9.4% sample rule. The GCN for 2026 is the same refit, checked against
2025; a model on both years, not a cross-fit. Climatology's 2026 score was already known (above).

## Decision 2 — The 2026 advice replay: criteria and plan

**AI proposal; owner accepted with three changes, 9 Nov 2026, before any 2026 replay result.**

**What is replayed.** The app's rule (`0014` Decision 4): `final_network`, firm "consider changing" from 60%, a
15-point gain, leaving at most 2 h earlier. The same method as `0013` and `0014` Finding 4: a trip is a sampled
2026 flight at 24, 6 or 2 h; its deadline is 30, 60 or 120 min after scheduled arrival; alternatives are on the
same route, leave 1 to 24 h after the forecast, arrive by the deadline, and are not known to be cancelled.
Alternatives are built for trips at risk under the model or climatology at the widest setting, as on 2025.

**Baselines,** as on 2025: the traveler's rule of thumb, and the schedule-only model under Murphy's rule.

**Pass or fail.** Net is per 1,000 trips, with a 95% interval resampling whole days.

| # | Test | Pass if | 2025 value |
|---|---|---|---|
| R1 | Murphy's net, 60 min | interval entirely above 0 | 1.15 (1.05 to 1.24) |
| R2 | Murphy minus rule of thumb, 60 min | interval entirely above 0 | 0.96 (0.87 to 1.04) |
| R3 | Murphy minus rule of thumb, 30 and 120 min | both intervals above 0 | 2.45, 0.23 |
| R4 | Murphy's net holds up, 60 min | at least half of 2025's (0.57 or more) | 1.15 |
| R5 | Rescued against needless, 60 min | rescued at least twice needless | 2,503 against 660 |
| R6 | Made worse, 60 min | at most 5% of changes | 125 of 4,586 (2.7%)† |

†`worse` column of `replay_final_network/baselines_firm60.csv` (2025), not shown in `0014` Finding 4. The `check` step
recomputes it before the 2026 run.

**Owner's changes:** (1) every count is shown with net per 1,000 and the rescued : needless ratio, since 2026 has
fewer trips than 2025 and raw counts do not compare; (2) R6's 2025 source is cited and recomputed; (3) Finding 1's
60-minute "60% and up" value corrected from 80.7% to 81.8%, in G6 and the bands table. The AI had copied the wrong
cell; `bands.csv` gives 0.8183. G6 still passes.

**Reported, not pass or fail:** every deadline's counts, each with net per 1,000 and rescued : needless; the replay's own 50% rule; the schedule-only model (under the 50% rule on
2025 it made no change at 60 or 120 min); thumb flags with no saved alternatives.

**Plan.** New file `scripts/eval_2026_replay.py`. It reuses the year-free parts of `replay_baselines.py` (`chances`,
`pick`, `tally`) and changes neither of the 2025 scripts, which hard-code 2025.

1. `check`: tally the **saved** 2025 replay with the new code. It must reproduce `baselines_firm60.csv` exactly.
2. `build tune 2025-01`: rebuild the alternatives for January 2025 trips only. Pairs and forecasts must equal the
   saved ones for those trips. This checks the build without the full 2025 rebuild.
3. `build test`: forecasts for the 2026 trips; the alternatives; their inputs (groups A to E, climatology, hidden
   aircraft inputs, communities and the GCN from `inputs` above); their forecasts by `final_network` and schedule-only.
4. `tally test`, once. Then the results go here, beside 2025.

**Known limits, before the run:** trips on 31 Aug 2026 lose alternatives after midnight, since there is no September
file (31 Dec 2025 had the same limit). Past schedules do not show seats. No real deadlines exist.

**Time:** estimated, not measured, about 35 to 50 minutes. The 2025 alternative inputs took 675 to 953 s.
