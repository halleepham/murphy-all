# 0017 — Communities and the GNN (PLAN layer 4)

Date: 7 Nov 2026. 2023–25 only; no 2026 outcome was read. One early count of rows and
airports did include the 2026 files. Scripts for the numbers below move into the repo with
this work. **Decisions are made; nothing under them is built yet unless a result says so.**

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

## AI-recommendation instances

| AI recommended | Owner | Why |
|---|---|---|
| Airports that go bad together | accepted | Readable groups, stable across years |
| Louvain, first for no new dependency | accepted after questioning | Owner would pay for a better result; the comparison showed the same best groups |
| Drop the shared-disruption rule | accepted | Same-route alternatives always share it |
| Two-layer GCN, routes then co-disruption, no aircraft edges | accepted | Simplest with weights; measured as cheap |
| Quick fit, refit, replay as the test | accepted | Keeps a tiny Brier gain from changing the model |
