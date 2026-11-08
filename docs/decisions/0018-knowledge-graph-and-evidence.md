# 0018 — Knowledge graph and evidence (PLAN layer 5)

Date: 7 Nov 2026. 2023–25 only; no 2026 outcome is read. **Part 1, the graph, is built and loaded** (Finding 1). GraphRAG,
vector retrieval and policies are next. Code: `murphy/graph.py`, `scripts/build_graph.py`, tests in
`tests/test_graph.py`.

## Human design

The owner asked for layer 5 options with a recommendation, and accepted all three
recommendations on 7 Nov 2026. The owner also said the Neo4j instance still holds the
previous project's graph and can be cleared.

## Decision 1 — The graph: a summary layer plus a slice of replay flights

**AI recommended, owner accepted.**

- **Summary layer:** airports, carriers, the five `0017` communities, route links and the
  co-disruption links the GCN was trained on (2023–24).
- **Replay slice:** the replay's forecasted flights, the alternatives Murphy offered for them
  (`0011`), and the METAR and TAF weather reports at the 30 airports that have them.
- **Aircraft (tail numbers) are left out.** BTS records the aircraft that flew, which is
  known only afterwards (`0014`). A graph that explained a risk through it would use
  hindsight.
- Every fact that arrives over time carries its `known_at`, so a query can ask only what was
  known at a forecast's `as_of`.

**Alternatives:** the summary layer alone (small, but multi-hop queries would be thin).

## Decision 2 — GraphRAG answers through fixed queries

**AI recommended, owner accepted.**

One Cypher query per question type (basic, multi-hop, analytics). The LLM (Groq, `0005`) only
picks the query and fills its parameters. Code validates the parameters and runs the query.
The LLM explains the returned rows and cites their IDs. It computes nothing.

**Alternatives:** the LLM writes Cypher itself (text-to-Cypher). Kept as a comparison.
**Baselines:** the same LLM with no retrieval, and BM25 over the same facts as text.

## Decision 3 — Vector retrieval: past days first, then policies

**AI recommended, owner accepted.** The corpora are from `0004` Decision 4.

1. **Similar past airport-days.** Given a forecast, find similar earlier airport-days; code
   computes what happened on them. Only days before the forecast count.
2. **Policies.** DOT commitments and a few carriers' contracts of carriage. To be collected.

Embeddings are `BAAI/bge-small-en-v1.5` (`0005`); the baseline is BM25 (`rank-bm25`). Both are
installed already. GCN airport scores rank which airports to search first (`0017` Decision 4).

## Decision 4 — The flight slice is 4–12 January 2025, not a whole month

**AI decided while building; within Decision 1.** I proposed one month. January 2025 is the
month with the most cancellations in 2025 (3.17% of all flights). Counted for that month:

| Part | Count |
|---|---|
| Replay flights | 53,317 |
| Alternatives not in the replay sample | 28,971 |
| Flight–alternative pairs | 39,221 |
| METAR reports | 26,113 |
| TAF reports | 8,561 |

That is about 117k nodes and 325k relationships, near Aura Free's limit. Sources disagree on
the limit: 200k / 400k or 50k / 175k (`0005` Decision 4). Nine days cover the month's two
storms with calm days around them. Cancelled share of all flights, by day:

| Day | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|
| Cancelled % | 1.2 | 8.1 | 11.0 | 3.0 | 1.0 | 10.3 | 16.8 | 4.7 | 0.5 |

The window is one constant in the build script, so it can be widened.

## Clearing the old instance

The old graph was backed up to `private/neo4j-backup-2026-11-07.json` (37,059 nodes,
147,881 relationships) before clearing. It is not read for this build (`0000`).

## Finding 1 — The graph as loaded, 7 Nov 2026

Loaded by `PYTHONPATH=. python scripts/build_graph.py load --clear`. Counts read back from Neo4j:

| Node | Count | | Relationship | Count |
|---|---|---|---|---|
| Flight | 33,280 | | DEPARTS_FROM, ARRIVES_AT | 33,280 each |
| Metar | 8,717 | | MARKETED_BY, OPERATED_BY | 33,280 each |
| Taf | 2,720 | | ALTERNATIVE_FOR | 29,624 |
| Airport | 341 | | REPORTED_AT | 11,437 |
| Carrier | 18 | | ROUTE_TO | 6,118 |
| Community | 5 | | CO_DISRUPTS | 803 |
| | | | IN_COMMUNITY | 336 |

6 node types and 9 relationship types. Flights: 15,588 replay flights and 17,692 alternatives
outside the sample; every ID matched a BTS record. 5 airports have no community (as in `0017`).
14,138 of the 15,588 replay flights have GCN inputs at 24 h; the GCN covers 100 airports.

**Checks, all 0:** METARs known before they were observed; forecasts with `as_of` at or after
departure; alternatives on a different route.

**By day, replay flights** (mean chance of missing a deadline 60 minutes after scheduled arrival):

| Day | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|
| Mean at 24 h | 0.086 | 0.106 | 0.210 | 0.185 | 0.100 | 0.086 | 0.149 | 0.173 | 0.115 |
| Mean at 2 h | 0.112 | 0.169 | 0.302 | 0.136 | 0.067 | 0.172 | 0.271 | 0.164 | 0.087 |
| Cancelled share | 0.009 | 0.080 | 0.106 | 0.030 | 0.014 | 0.097 | 0.183 | 0.038 | 0.006 |

**Read:** the 9 Jan storm was not in the 24 h forecasts (0.086, the same as a calm day) and was in
the 2 h ones.

**One example, every fixed query** (`murphy.graph.QUERIES`), flight
`2025-01-10:AA3104:ATL-DFW:1410` at 24 h, `as_of` 2025-01-09 19:10 UTC:
- Chance of missing: 0.419 at 24 h, 0.777 at 6 h, 0.717 at 2 h. Best alternative at 24 h:
  `DL414` at 11:24, 0.156.
- The latest ATL METAR known then (`ATL:2025-01-09T18:52`) was clear. The latest TAF
  (`202501091733-KFFC-FTUS42-TAFATL`) forecast snow and sleet at ATL from 12Z on the 10th and freezing rain from
  15Z. The flight was scheduled to leave at 19:10Z.
- Hindsight: cancelled (`mkt_2025_01.zip`).

**Limits:** CO_DISRUPTS neighbors without one of the 30 weather airports return a blank METAR
(RDU here). Cancelled flights have no announcement time, so their outcome is known at scheduled
departure (`0016`). The course's look at 2–3 existing ontologies is skipped: owner's
decision, 7 Nov 2026, as the graph is built and the poster does not need it.

## Finding 2 — Would one-stop connections add alternatives? 7 Nov 2026

**Human design:** the owner asked whether communities could tell if an alternative shares the
trip's risk. With same-route alternatives they cannot: every alternative shares both airports.
Connections through a hub are where they could. The owner asked for a check before deciding.

`PYTHONPATH=. python scripts/connections_check.py 30 60`, 22 s. The 46,764 replay forecasts in
the window (15,588 flights × 3 leads), deadline 60 min after scheduled arrival. Direct: the
`0013` rule. Connection: same marketing carrier on both legs, any hub, leg 2 leaving at least
the assumed minimum connection time (MCT) after leg 1's scheduled arrival. "Worked" is
hindsight: it actually arrived by the deadline, and leg 1 actually landed MCT before leg 2
left. The best option is picked in hindsight and seats are unknown, so this is an **upper bound**.

| | MCT 30 | MCT 45 | MCT 60 |
|---|---|---|---|
| Forecasts with a direct alternative | 62.6% | 62.6% | 62.6% |
| With a connection | 50.2% | 48.7% | 46.8% |
| With a connection and no direct | 7.3% | 6.7% | 6.0% |
| Trip missed (of 46,764) | 7,809 | 7,809 | 7,809 |
| … a direct alternative worked | 3,859 | 3,859 | 3,859 |
| … a connection worked | 3,041 | 2,953 | 2,841 |
| … only a connection worked | 506 | 460 | 415 |

Median, when any exists: 15 connections through 3 hubs (MCT 45).

**At MCT 45, by lead, of 2,603 misses each:**

| Lead | Direct worked | Only a connection worked |
|---|---|---|
| 24 h | 2,260 | 223 |
| 6 h | 1,232 | 233 |
| 2 h | 367 | 4 |

Of the 460, 263 trips had no direct alternative at all; 197 had direct ones that all failed.

**Read:** connections add rescues in 5.9% of misses (460 of 7,809), on top of 49.4% from direct
flights, both as upper bounds. Almost none at 2 h. The 24 h rescues are inflated: a flight up to
23 h earlier than the trip counts as an alternative, which few travelers could take.

## Decision 5 — Alternatives stay direct, same route

**Owner decided, 7 Nov 2026, after Finding 2.** Options put to the owner:

- **A. Keep direct alternatives only (chosen).** State the limit with Finding 2 as evidence.
- B. Add same-airline one-stop connections: forecasts for each leg, a rule for making both,
  shared risk between legs as the comparison, then rerun the change rule, replay, app and graph.
  About a day of sessions and 1–3 h of machine time. At best 5.9% more missed trips rescued.
- C. Measure only whether same-community airports fail together. A finding, no change for the
  traveler.

**Why:** B's best case is small, and the redo is large. **Implication:** communities stay a
forecast input (a slight calibration gain, `0017`) and an explanation of regional trouble
(the `community_day` query). They do not judge whether an alternative shares the trip's risk:
every alternative shares both airports. **Limit to state:** connections and nearby airports are
not offered; Finding 2 bounds what that leaves out. Not decided.

## AI-recommendation instances

| AI recommended | Owner | Why |
|---|---|---|
| Summary layer plus a replay slice, no aircraft | accepted | Multi-hop queries without hindsight |
| Fixed queries; LLM picks and explains | accepted | The LLM never computes |
| Past days first, then policies | accepted | Data is here; policies must be collected |
| 9 days, not a month | AI decided while building | A month is near Aura Free's limit |
| Check connections before deciding; lean A | accepted A | Best case 5.9% of misses; large redo |
