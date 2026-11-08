# 0022 — Ranking airports with the GCN before retrieval (PLAN layer 5, `0017` Decision 4)

Date: 8 Nov 2026. 2025 only; no 2026 outcome was read. **Built and measured** (Findings 1–3).
Code: `murphy/forecast/rank.py`, `scripts/gcn_rank_eval.py`, tests in `tests/test_rank.py`.
Results: `data/forecast/network/rank_neighbors.csv`, `rank_national.csv`, `rank_example.csv`
(gitignored); log `data/forecast/logs/gcn_rank.log`. Run time 63 s.

What the traveler would get: when the app asks "why is this flight at risk?", the airports whose
weather it shows are the ones most likely to go bad next, not simply the ones that usually move
with the origin. **In the app behind a switch that is off** (Decision 6).

## Checks before building, 7 Nov 2026

Asked for by the owner, so nothing would need rerunning.

- The six saved GCN arrays are 26,304 hours (every hour of 2023–25) by 100 airports, values 0–1,
  none blank.
- Rebuilding the targets reproduces `0017` Finding 2 exactly: 2025 error 0.011916 (no edges) and
  0.012140 (co-disruption). So the hours and airports line up.
- `communities.csv`, which sets the airport order, was written before every array.
- `gcn_co_avg.npy`, the one the forecast uses, takes its 2025 hours only from models trained on
  2023–24. Its own error was never recorded: **0.011775**, mean predicted 0.234 against a true 0.230.
- 9.3% of flights in the graph window (4–12 Jan 2025) leave airports outside the 100 and have no
  GCN score. From 03:00 to 07:00 UTC only 12–29 airports have a target.
- Suite before starting: 178 passed.

## Decisions 1–5

**AI recommended, owner accepted, 7 Nov 2026, before any scoring.**

1. **Where the ranking is used:** the origin's co-disruption neighbors in the `why` query, keeping
   the top 3 (the airports whose weather is fetched). Second, all 100 airports, keeping the top 10,
   the course's own example.
2. **The truth:** each airport's late-or-cancelled share of departures scheduled in the next 3
   hours, the GCN's own target. Second: that share minus the airport's usual for the hour and month.
3. **The score:** the share of the 3 (or 10) picks whose true share is at least the 3rd (10th)
   largest, so ties never count against a ranking. Intervals resample whole days. An airport counts
   only with ≥ 10 departures in the window, an hour only with ≥ 20 such airports, a neighbor list
   only with more than 3 such airports. 3, 10 and 20 are AI choices, untested.
4. **Compared with:** today's order (link weight), the usual for the hour, the last 2 hours, random,
   and the GCN with no edges (the ablation). The single co-disruption seed is shown too, for a fair
   one-seed comparison with no edges.
5. **App change:** only if the GCN beats today's order; decided after the results.

## Finding 1 — The GCN picks better airports than today's order

Neighbors, top 3. 653,549 airport-hours on 6,963 hours of 2025. Hit share, and the true late share
of the 3 picked:

| Ranking | Hit share (95%) | vs GCN (95%) | Picked true share |
|---|---|---|---|
| **GCN, 3-seed average (the forecast's)** | **0.450 (0.445 to 0.455)** | | **0.285** |
| GCN co-disruption, seed 0 | 0.448 | −0.002 (−0.003 to −0.002) | 0.285 |
| GCN no edges, seed 0 | 0.460 | +0.010 (+0.008 to +0.012) | 0.287 |
| Last 2 h at this airport | 0.419 | −0.032 (−0.034 to −0.029) | 0.273 |
| Usual for the hour | 0.363 | −0.088 (−0.092 to −0.082) | 0.252 |
| Today's order (link weight) | 0.299 | −0.152 (−0.156 to −0.146) | 0.238 |
| Random | 0.294 | −0.156 (−0.161 to −0.150) | 0.229 |

**All 100 airports, top 10** (6,963 hours): GCN 0.397, no edges 0.405, last 2 h 0.357, usual 0.261,
random 0.176. The order is the same. Against the excess over usual, the order is the same again,
except that the usual has nothing to say and falls to random (`rank_*.csv`).

**Read:** today's order is no better than random at finding the airports that will be worst in the
next 3 hours. Link weight says which airports *usually* move together, not which are bad *now*. The
GCN beats every simpler order, and the last 2 hours is the closest.

## Finding 2 — The edges are not what helps

The GCN with no edges ranks slightly better than the forecast's GCN, on both truths and both
lists, and every one of those intervals excludes zero. The single co-disruption seed ranks slightly
worse than it. A paired interval between the two single seeds was not computed. This matches `0017` Finding 2 (edges tie or lose on
the GCN's own target). So the gain comes from a learned model of each airport's own state, not
from message passing. A GNN is not shown to be needed for ranking. The forecast's model is still
used here, because that is the one the app has.

## Finding 3 — One example, chosen before scoring

Atlanta's neighbors at 15:00 UTC on 10 Jan 2025, the snow day; ATL's own true share was 1.0. Scored
by the same code (`rank_example.csv`):

| Ranking | Picks | Hits | Picked true share |
|---|---|---|---|
| GCN | MEM, BNA, TYS | 3 of 3 | 0.837 |
| Last 2 h | MEM, BNA, TYS | 3 of 3 | 0.837 |
| Today's order | CLT, RDU, BNA | 1 of 3 | 0.503 |
| Usual | FLL, SRQ, DTW | 0 of 3 | 0.259 |

True top 3: MEM, TYS, BNA. Here the last 2 hours does as well as the GCN.

## Something odd

`0017` Decision 1 links each airport to its 8 most correlated. But summing the 2023 and 2024
graphs, and links running both ways, gives a median of 13 neighbors, up to 39. ATL has 28. So the
`why` query today fetches weather for every one of them, and the evidence list gets long. A top 3
would also shorten it.

## Decision 6 — In the app, behind a switch that is off

**AI recommended, owner accepted, 8 Nov 2026.** The GCN beats today's order (Finding 1), so the
`why` question can keep the origin's own row and the top 3 neighbors by GCN score, each shown with
that score. It is off unless `MURPHY_GCN_RANK=1`.

- **Why off:** explanations are cached by their exact evidence (`murphy/graphrag.py`, `llm`).
  New evidence means the app would call Groq live, and the `0019` "why" marks would no longer
  match the page. The owner did not want Groq used on 8 Nov.
- **To turn on, on a Groq day:** set the variable, rerun the `why` answers in
  `scripts/graphrag_eval.py`, and compare them with the `0019` marks.
- **How:** Python reorders the query's rows using `gcn_co_avg.npy`, from the top of the hour at or
  before `as_of`. No graph rebuild. Neighbors with no score go last. Without the score files the
  evidence is unchanged. The page's provenance line names the order used.
- **Rejected:** the last 2 hours as the order. Simpler and close (0.419 against 0.450), but loses
  the GNN demo the course asks for.

**Live check, Neo4j only, no LLM call** (flight `2025-01-10:DL2901:ATL-MSP:1205`, 2 h lead,
`as_of` 15:05 UTC):

| Switch | `why` evidence rows | Neighbors shown |
|---|---|---|
| Off | 9 | CLT, BNA, TPA, DTW, BWI, MSP, DCA (link-weight order) |
| On | 5 | BNA 76%, CLT 40%, TPA 38% |

The scores equal the saved array for those airports (`rank_example.csv`).

**Something odd:** only 7 of ATL's 28 neighbors have a weather report in the graph. MEM and TYS,
truly the worst that hour, have none, so they cannot be shown with the switch on or off. The GCN
can only choose among neighbors that have weather.

## Limits

- 2025 has been seen before; the sealed 2026 test is untouched.
- 9.3% of graph-window flights leave airports with no GCN score; they would keep today's order.
- Neighbor lists overlap, so airport-hours are not independent; intervals resample days to allow
  for it.
- Hit share measures retrieval, not the answers. Whether better-ranked evidence gives better
  GraphRAG answers is untested, and testing it needs Groq budget.

## AI-recommendation instances

| AI recommended | Owner | Why |
|---|---|---|
| Rank the `why` neighbors; national top 10 second | accepted | Real retrieval in the app; the course's example as well |
| Truth is the GCN's own target; excess second | accepted | Fixed before scoring |
| Tie-aware hits, ≥ 10 departures, ≥ 20 airports | accepted | Small windows make noisy truths |
| Five comparisons, including today's order and no edges | accepted | Today's order is the real baseline; no edges isolates the graph |
| Change the app only if the GCN beats today's order | accepted | Decided after results |
| GCN order in the app, switch off until a Groq day | accepted | Keeps cached answers and `0019` marks valid |
