# 0017 — Communities and the GNN (PLAN layer 4)

Date: 7 Nov 2026. 2023–25 only; no 2026 outcome was read. One early count of rows and
airports did include the 2026 files. Scripts for the numbers below move into the repo with
this work. **Built and measured** (Findings 1–4 below). Code: `murphy/forecast/network.py`,
`murphy/forecast/gcn.py`, `scripts/network.py`, tests in `tests/test_network.py`. Results are in
`data/forecast/network/` (gitignored), logs in `data/forecast/logs/network_*.log`.

## Quick check before deciding

**Human design:** the owner asked to read the course files, then see options with real results.

Communities came from 2023–24 only, over the 100 airports with at least 20,000 departures in
those two years. The screen stacked each signal on `final_clean`'s saved 2025 forecasts, fit on
half the days and scored on the other half. It is a screen, not a refit.

**Late Brier, all leads, 923,865 forecasts, base 0.14794:**

| Signal added | Change | 95% interval, resampling days |
|---|---|---|
| Whole country, no graph | −0.00015 | −0.00036 to +0.00006 |
| Airports linked by routes | −0.00020 | −0.00040 to −0.00000 |
| Same community | −0.00033 | −0.00052 to −0.00013 |

**Read:** small. Recalibrating by hour and lead alone gains 0.00034. Weather gained 0.0048 on
late Brier (`0010` Finding 2), on different rows.

**Limits:** 81.6% of 2025 forecasts, those between the 100 airports. 2025 has already been seen.

The first run of the screen had a bug: the label is `0-15`, not `0_15`, so on-time flights counted
as late. It showed 40.4% late against 22.5% predicted, which is how it was caught. The table is
after the fix (23.8% late).

## Decision 1 — A community is a group of airports that go bad together

**AI recommended, owner accepted, 7 Nov 2026.**

For each airport and 3-hour block: the share of departures 15+ minutes late or cancelled, minus
that airport's usual for the hour and month. Correlate this between every pair of airports. Link
each airport to its 8 most correlated, weighted by correlation. Then find groups. The 8 is an AI
choice and is untested.

Example, 11 March 2024, 18:00 UTC: LGA 85.7% against a usual 21.3%; EWR 67.6% against 19.2%;
SEA 23.1% against 19.8%; JFK 23.4% against 22.0%. In 2024, EWR–LGA correlate at 0.708, ATL–SEA at
0.282, and the median pair at 0.224.

| Option | Result on 2023–24 | Outcome |
|---|---|---|
| **Airports that go bad together** | 5 groups, modularity 0.556, 2023 vs 2024 agreement 0.86 | **Chosen.** Regional input, map zones, plain explanations |
| Airports linked by flights | 3 broad groups, modularity 0.222, agreement 0.88 | Rejected: mostly shows the network's shape |
| Flights or aircraft | Not tested | Rejected: tail numbers risk the hindsight leak (`0014`), and far larger |

The groups read as Northeast, West, South-central, Midwest and Southeast, with no geography as
input. Those names are AI labels. The method shows that airports move together, not why.

**Course asks:** 1–2 community types and 2–3 features. One type; the features are co-disruption
over time, the usual level for hour and month, and link weight.

## Decision 2 — Louvain, run many times

**AI recommended Louvain, at first only to avoid a dependency. The owner asked why and said a
dependency was fine for a better result.** So both were run, 30 times each, on the 2023 graph:

| | Louvain | Leiden |
|---|---|---|
| Groups | Always 5 | 4 or 5 |
| Best modularity | 0.5575 | 0.5575 |
| Mean modularity | 0.5496 | 0.5564 |
| Agreement between runs | 0.831 | 0.917 |
| 2023 vs 2024 agreement (one run each) | 0.862 | 0.792 |
| Internally disconnected groups | 0 | 0 |

The best run of each gives identical groups (agreement 1.0), so Leiden gives steadier runs, not a
better answer, on this graph. **Owner accepted Louvain**: run many seeds and keep the best. Leiden
stays a fair alternative, with wheels for this machine (`leidenalg`, `igraph`, `texttable`).

## Decision 3 — Drop "an alternative shares the disruption" as a rule

**AI recommended, owner accepted, 7 Nov 2026.** `0010` proposed it, but all 726,628 saved
alternatives are on the same route as the current flight, so they always share airports and
community. Nor were alternatives clearly more over-promised when the region was disrupted: true
minus predicted late, from calm to worst, was 3.0, 3.7, 2.2 and −3.1 points. The regional state
stays as evidence on the screen. The rule would only mean something with other routes or nearby
airports, which is new scope.

The forecast itself runs low when a region is disrupted: 4.1 points at the 50–90% band, 0.7 when
calm. That is the gap a network input could close.

## Decision 4 — The GNN: a two-layer GCN over airports

**AI recommended, owner accepted, 7 Nov 2026.** Each hour's graph has the 100 airports. Each
airport's current state predicts its share of late or cancelled departures over the next 3 hours,
and that prediction feeds the forecast (`0010` Decision 6, option B). About 1.75M node-hours for
2023–24.

- **Edges:** fixed routes from 2023–24, then the co-disruption graph as a second run. No aircraft
  edges (`0014`).
- **Compared with:** the current state alone, and the same network with no edges. The no-edge run
  shows what message passing adds.
- **Course example:** airport scores rank airports before retrieval, as a small demo in layer 5.
- **Rejected for now:** GraphSAGE and GAT (GCN takes edge weights and all 100 nodes are always
  present); STGNN, unless the simple one shows promise (`docs/PLAN.md`).

**Expected:** a small gain at best, given the table above. A null result is still reported.

**Time, measured on random numbers of the right shape, for timing only:** 18 s per pass over the
hours, under 1 GB, 1,505 parameters, no GPU.

## Decision 5 — What counts as "helps"

**AI recommended, owner accepted, 7 Nov 2026.**

1. **Quick fit:** a quarter-sized fit with and without each input. Multiclass Brier on 2025, with
   intervals resampled by day.
2. **Retrain:** one full refit, only if an interval is entirely below zero.
3. **Final test:** rerun the replay. Keep the input only if net benefit per 1,000 is not worse.

A small Brier gain alone does not change the model.

## Finding 1 — The communities

From 2023–24: 5 groups, modularity 0.5532, best of 30 Louvain seeds over the summed yearly graphs.
341 airports had departures in 2023–24. The 100 big ones are grouped directly; smaller airports join
the group they fly to most. 336 airports get a group; GST, PSG, SPN, WRG and YAK get none.
Groups: `network/communities.csv`.

**Inputs made from them** (group f): flights and late share at the origin's and destination's
group in the 2 hours before the forecast, leaving out the airport itself. Group n is the same
for the whole country, the simpler baseline. 2026 rows are blank.

## Finding 2 — The GCN

Squared error on each big airport's late share over the next 3 hours, 2025, weighted by flights.
2023 is predicted by a model trained on 2024 and the reverse; 2025 from both. True 2025 late share
0.230. From `network/gcn_compare.csv` and `network/gcn_seeds.csv`:

| Model | Error, seed 0 | Seeds 1, 2 |
|---|---|---|
| Usual for the hour | 0.02730 | |
| Last 2 h at this airport | 0.02440 | |
| GCN, no edges | 0.01192 | 0.01183, 0.01188 |
| GCN, co-disruption edges | 0.01214 | 0.01195, 0.01183 |
| GCN, routes | 0.01306 | |
| GCN, routes, 8 busiest per airport | 0.01247 | |

**Read:** the GCN halves the error of the simple baselines, but message passing adds nothing on
its own target: co-disruption edges tie with no edges (seed 0 difference +0.00022, interval −0.00008
to +0.00048), and route edges are worse. Trimming routes to the 8 busiest helped but stayed worse.
Seed 0 co-disruption runs high (mean 0.246 predicted against 0.230).

## Finding 3 — Leak checks, all passed

- At every top-of-hour forecast (207,436 rows), the GCN's input window matches the forecast's own
  2-hour window, and wiping everything after the forecast time changes nothing.
- On 300,000 sampled rows of each set, the own-airport window equals the existing current-state
  input (group C) exactly.
- Hidden-flight probe (`0014`): AUC 0.7682 with nothing, 0.7696 with hidden inputs, 0.7702 with the
  new inputs. A leak would push this far up.
- A deliberate peek control's top tenth reaches 0.0549 on the leak screen; the new inputs reach
  0.032–0.036. The GCN's top tenth is 51% late, against 71% for the forecast's own top tenth.

## Finding 4 — Quick fits, refit and replay

**Quick fits** (225 rounds on the fit rows, multiclass Brier on 2025, change from base, 95%
interval by day; `network/quick_compare.csv`):

| Inputs | Change | Interval |
|---|---|---|
| n, whole country | −0.00022 | −0.00031 to −0.00012 |
| f, communities | −0.00041 | −0.00050 to −0.00031 |
| GCN no edges, seed 0 (h) | −0.00061 | −0.00071 to −0.00049 |
| GCN co-disruption, seed 0 (g) | −0.00096 | −0.00121 to −0.00073 |
| GCN no edges, seed 1 (k) | −0.00055 | −0.00069 to −0.00041 |
| GCN co-disruption, seed 1 (i) | −0.00089 | −0.00114 to −0.00067 |
| f + GCN co-disruption, 3-seed average (fm) | −0.00103 | −0.00127 to −0.00082 |

Communities beat the whole country (f − n −0.00019, −0.00027 to −0.00011). Co-disruption edges beat
no edges as a forecast input on both seeds (g − h −0.00035; i − k −0.00034, −0.00050 to −0.00019),
though they tie on the GCN's own target. Seed 0 alone with f did slightly better than the average
(fm − fg +0.00011), but **fm was chosen** so as not to pick a seed on 2025. The intervals are
entirely below zero, so one full refit was run.

**Full refit** `final_network`: groups abcdefm, 84 inputs, 300 rounds, fit 2,504 s. On all
2,070,453 forecasts of 2025 (`network/final_compare.csv`):

| Lead | Multiclass Brier change | Interval | Late Brier change | Interval |
|---|---|---|---|---|
| All | −0.00093 | −0.00113 to −0.00077 | −0.00058 | −0.00074 to −0.00046 |
| 2 h | −0.00096 | −0.00114 to −0.00080 | −0.00050 | −0.00061 to −0.00040 |
| 6 h | −0.00102 | −0.00126 to −0.00080 | −0.00072 | −0.00090 to −0.00054 |
| 24 h | −0.00082 | −0.00108 to −0.00059 | −0.00053 | −0.00075 to −0.00035 |

Predicted late share rises from 0.2224 to 0.2249, against a true 0.2361: still low, less so.

**Replay** (the chosen rule, all trips, net per 1,000; `replay_final_*/baselines.csv`):

| Deadline | `final_clean` | `final_network` | Changes | Worse off |
|---|---|---|---|---|
| 30 min | 4.62 (4.23 to 4.97) | 4.74 (4.34 to 5.11) | 21,249 → 21,897 | 663 → 716 |
| **60 min** | **1.63 (1.48 to 1.75)** | **1.64 (1.49 to 1.78)** | 7,466 → 7,600 | 248 → 275 |
| 120 min | 0.42 (0.38 to 0.48) | 0.44 (0.39 to 0.50) | 2,388 → 2,443 | 132 → 136 |

The 3.84 named earlier was `final_leads` (`0014`), not `final_clean`; 1.63 is the right comparison.
Net is not worse at any deadline, so **by Decision 5 the inputs are kept.** The gain in net is
within noise: the intervals overlap almost entirely, and a paired interval was not computed. The
model also acts a little more, and a few more travelers end up worse off.

**Conclusion:** network inputs make the forecast slightly better calibrated and leave the
recommendations about the same. Communities are worth more as explanation ("your region is having
a bad hour") than as accuracy. The GCN's edges help the forecast but not the GCN's own target, so
how they help is not shown. **Owner decided, 7 Nov 2026: switch the app to `final_network`.** `MODEL` in `murphy/app/server.py`
names it, and `scripts/build_app_data.py` builds from that model's replay. Rebuilt: 2,070,453 trips,
776,125 alternatives for 175,985 trips (was 726,628 for 165,493), because the new model flags more
trips. Track record at 60 min: kept 7.8% predicted vs 8.5% true miss; uncertain 48.0% vs 53.3%;
high 74.5% vs 82.0%.

## AI-recommendation instances

| AI recommended | Owner | Why |
|---|---|---|
| Airports that go bad together | accepted | Readable groups, stable across years |
| Louvain, first for no new dependency | accepted after questioning | Owner would pay for a better result; the comparison showed the same best groups |
| Drop the shared-disruption rule | accepted | Same-route alternatives always share it |
| Two-layer GCN, routes then co-disruption, no aircraft edges | accepted | Simplest with weights; measured as cheap |
| Quick fit, refit, replay as the test | accepted | Keeps a tiny Brier gain from changing the model |
| Average 3 GCN seeds, not the best one | accepted (rule agreed in advance) | Avoids picking a seed on 2025 |
