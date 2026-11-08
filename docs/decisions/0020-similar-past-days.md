# 0020 — Similar past airport-days (PLAN layer 5, part 3)

Date: 7 Nov 2026. Builds on `0018` Decision 3 (past days first, then policies) and `0004`
Decision 4. Built 7 Nov 2026 (below). No LLM is used: retrieval and every number are code.

What the traveler gets: beside a forecast, "on the 10 past days at this airport whose forecast
looked most like today's, X% of departures left 15+ min late or were cancelled", with each day
listed (airport, date, forecast text) so it can be checked.

All four decisions below: **AI recommended, owner accepted (7 Nov 2026).**

## Decision 1 — Each airport-day is a plain-English sentence written by code

Code reads the TAF fields for the day and writes, for example, "ORD, a Tuesday in January.
Snow, clouds at 800 ft, 1 mile visibility, wind 25 kt gusting 35." Both BM25 and the
embeddings get the same fair input, and every word comes from a field.

**Alternatives:** A, the raw TAF text. Real text, but `bge-small` was not trained on codes like
`BKN008 TSRA`. C, numbers only (weather and calendar) with nearest neighbors. Kept as a
comparison method, not the design.

## Decision 2 — Candidates: same airport, earlier days only, top 10

- Same airport only, so the claim stays "what happened here on days like this". All airports
  would give more matches for rare weather but mixes airports that handle snow differently.
- A past day counts only if it ended before the forecast was made. The query uses the TAF known
  at forecast time, as the model does (`asof.taf_as_of`).
- Corpus: 2023–2025, the 30 airports of `0007`. 2026 stays sealed (`PLAN` step 8).

## Decision 3 — Scored objectively, against four simpler methods

Every 2025 airport-day is a query. Measure how well the mean outcome of its 10 retrieved days
predicts that day's actual outcome (error and rank correlation). Methods on the same days:

1. `bge-small` embeddings
2. BM25 (`rank-bm25`), the course's baseline
3. numeric nearest neighbors (Decision 1, option C)
4. same airport, same month average
5. random earlier days (floor)

If embeddings do not beat 3 and 4, that is the finding and is reported as one. Then AI marks 5
retrievals by hand with evidence; the owner checks the marks.

## Decision 4 — Evidence only, not a model input yet

Testing it as a model input means retraining; `PLAN` says "if time allows". It can come after
the app is finished.

**Thin evidence:** a query day with no TAF, or too few close earlier days, says so instead of
showing a percent. The cutoff is set from the measured similarities and reported here.

## How it works (built 7 Nov 2026)

`murphy/pastdays.py`; build with `python -m murphy.pastdays` (~10 min: corpus ~5, embeddings ~5).
Comparison: `PYTHONPATH=. python scripts/pastdays_eval.py` (158 s). Tests: `tests/test_pastdays.py`.

- 32,880 airport-days (30 airports x 1,096 days, 2023-2025), all with a TAF.
- TAF: the latest known before local midnight, read over 06:00-22:00 local. A prevailing period
  runs until the next starts; the last until issue + 30 h, as `forecast/features.py` reads it.
  Checked: 20 random days match `asof.taf_as_of`.
- Outcome: departures with `duplicate_flag = 'N'`; late = cancelled or departed 15+ min late.
- BM25's term weights use the airport's whole 2023-2025 corpus. Only word statistics, never
  outcomes, so no outcome leaks; stated for completeness.

## Finding 1 — Embeddings tie BM25 and plain numbers; all three beat the simpler averages

All 10,950 airport-days of 2025 as queries (`data/pastdays/eval_summary.csv`). Error is in
late share (0.083 = 8.3 points). Interval: 95% paired bootstrap, 1,000 resamples, of each
method's error minus the embeddings'.

| Method | Mean abs. error | Spearman, pooled | Spearman, within airport | Error minus embed (95% CI) |
|---|---|---|---|---|
| embed (bge-small) | 0.0829 | 0.488 | 0.467 | — |
| bm25 | 0.0827 | 0.493 | 0.464 | -0.0002 (-0.0010, 0.0007) |
| numeric neighbors | 0.0821 | 0.500 | 0.476 | -0.0008 (-0.0017, 0.0000) |
| same-month average | 0.0913 | 0.331 | 0.274 | +0.0084 (0.0075, 0.0093) |
| random earlier days | 0.1015 | 0.110 | -0.007 | +0.0186 (0.0173, 0.0199) |

Matching on the day's forecast helps: about 0.8 points less error than the month average. How
the match is made does not matter here; embeddings add nothing over BM25 or plain numbers.

## Finding 2 — Low similarity means worse evidence

Mean similarity of the 10 days (embed) against error, 2025, in fifths: lowest fifth 0.108,
highest fifth 0.064. Below 0.920 (the 2025 5th percentile, 540 days): error 0.099 against
0.082 above.

## Finding 3 — Five retrievals marked by AI (owner to check)

| Query | Actual | Embed | Mark |
|---|---|---|---|
| EWR 19 Jan 2025, snow, 0.5 mi | 41.3% | 30.9% | Partly relevant: of the top 4, 2 forecast snow, 1 snow only at times, 1 rain only |
| BNA 19 May 2025, showers, TS at times | 31.8% | 29.4% | Relevant: all 4 showers or storms, same month |
| BWI 23 Apr 2025, calm | 25.6% | 26.1% | Relevant match, but its days range 6.6-37.6%: calm weather does not settle it |
| IAH 24 Apr 2025, lowest similarity | 32.7% | 25.6% | Weak matches; correctly low similarity (0.866) |
| ATL 10 Jan 2025, freezing rain, largest error | 98.9% | 29.1% | Wrong: no earlier ice day at ATL; similarity 0.871 |

Noticed: the sentence starts with weekday and month, and top matches nearly always share both.
The calendar may crowd out the weather in the embeddings. Not tested.

## Decision 5 — Was it helpful? Yes, modestly; it goes in the app, with embeddings

**AI recommended, owner accepted (7 Nov 2026).** Findings 1-3: matching on the forecast misses
by about 1 point less than the month average and ranks bad days from good ones far better
(0.47 against 0.27 within airport). It also shows when it has no close match. The app uses
embeddings: they are the vector retrieval the course asks for, and tie the simpler methods.
The tie is reported as a finding, not hidden.

**Alternatives:** B, plain numbers (simplest; very slightly best, inside the interval).
C, leave it out and record it as tried.

Not tested: whether it beats the flight model, which reads the same forecast. It is evidence
the traveler can check, not a better prediction.

## Decision 6 — Thin evidence below 0.920 mean similarity

**AI recommended, owner accepted.** Below 0.920 (the 2025 5th percentile, Finding 2) the app
says "no close past days" and shows no percent; the days are still listed to inspect. Also thin:
no TAF for the day, or fewer than 10 earlier days. Flags both bad cases in Finding 3.

## Decision 7 — Show the range of the 10 days beside their average

**AI recommended, owner accepted.** The 10 days can disagree widely (BWI, calm: 6.6-37.6%), so
the range is shown as the uncertainty.

## In the app (built 7 Nov 2026)

`GET /api/pastdays?flight_id=&lead_h=` in `murphy/app/server.py`, which calls
`murphy.pastdays.similar`. The page's section "Similar past days at <origin>" comes after the
track record. It says the figure is every departure from the airport that day, not the
traveler's flight. "See the days" lists the 10 days with date, late share, counts, similarity,
forecast text and TAF product ID. The query reads the TAF known at the forecast time, so it
changes with the lead-time control. Checked live: UA691 IAH, 16 Jun 2025, was 29% at 24 h (no
weather forecast) and 39% at 2 h (thunderstorms forecast). AA3937 from AVP says no weather data.
The first call loads the model (about 13 s); later calls take about 0.1 s.

**Limitation:** IEM leaves the wind speed blank for light variable wind (`VRB03KT`), so the
sentence leaves the wind out. `forecast/features.py` reads the same field.

## AI-recommendation instances

| AI recommended | Owner | Why |
|---|---|---|
| Code-written sentence per airport-day | accepted | fair input for BM25 and embeddings |
| Same airport, earlier days, top 10 | accepted | keeps the claim local; no leakage |
| Five-way comparison on 2025 | accepted | objective; includes simpler methods |
| Evidence only for now | accepted | retraining waits for the finished app |
| Add to the app with embeddings | accepted | helps modestly; meets vector retrieval; ties simpler methods |
| Thin below 0.920 mean similarity | accepted | 5th percentile; low similarity misses more |
| Show the 10 days' range | accepted | the days can disagree widely |

## Change, 8 Nov 2026: the sentences say mph; index rebuilt and re-scored

**Owner** (with `0023`'s plain-words rule): the day sentences should not say "kt". `describe` now
writes wind in mph (knots x 1.15078); the windy threshold is unchanged (20 kt, or gusts 30 kt).
Index rebuilt (`python -m murphy.pastdays`, 9 min): 32,880 airport-days, every field but the text
identical to before, no "kt" left. The old index and scores are kept in `private/pastdays-kt-backup/`.

Re-scored with `scripts/pastdays_eval.py` (10,950 queries, 2025):

| Method | MAE, kt (7 Nov) | MAE, mph (8 Nov) | Error minus embed, mph (95% CI) |
|---|---|---|---|
| embed | 0.0829 | 0.0831 | — |
| bm25 | 0.0827 | 0.0828 | -0.0003 (-0.0012, 0.0006) |
| numeric | 0.0821 | 0.0821 | -0.0010 (-0.0019, -0.0001) |
| month | 0.0913 | 0.0913 | +0.0083 (0.0074, 0.0091) |
| random | 0.1015 | 0.1015 | +0.0184 (0.0171, 0.0197) |

Spearman within airport, embed: 0.467 before, 0.467 after. **What changed:** plain numbers are now
ahead of embeddings by 0.1 point of error, and the interval just excludes zero (before, it just
touched it). Decision 5 kept embeddings because they tied; it is now a very small loss. Kept for
now, as the course's vector retrieval; the owner may switch to plain numbers.

**Thin evidence (Decision 6):** the cutoff is the 2025 5th percentile of mean similarity, which
moved from 0.920 to 0.930 with the new wording (at 0.920 only 248 days would be thin). Set to
0.930: 562 days below, error 0.102 against 0.082 above, the same split as before. Error by fifth
of similarity, lowest to highest: 0.105, 0.094, 0.079, 0.072, 0.065.

## Decision 8 — The app searches by plain numbers, not embeddings (8 Nov 2026)

**Owner asked** why the app used embeddings when they scored worst. **AI's answer:** Decision 5
chose them as the course's vector retrieval, while the three methods tied; after the mph rebuild
plain numbers are measurably, if barely, better (above). **Owner decided:** switch Similar days to
plain numbers; the Rules tab (`0021`) is the app's vector retrieval. Supersedes Decision 5's choice
of method; its finding stands.

- `similar` now calls `search(..., "numeric")`: nearest neighbors on standardized forecast numbers
  (visibility, cloud base, wind, gusts, weather-type flags) and calendar (month, weekday), same
  airport, earlier days only, top 10. The app loads the corpus only: no embedding model at run time.
- **Thin evidence (Decision 6), re-derived for distance:** thin when the mean distance of the 10 days
  is above 3.16, the 2025 95th percentile (548 days). Error above it 0.135, below 0.079. Error by
  fifth of distance, closest to farthest: 0.061, 0.065, 0.075, 0.096, 0.113. A sharper warning than
  embedding similarity gave (0.102 against 0.082).
- Checked on live trips: F9 4195 LGA, 9 Jan 2025, mean distance 1.68, answered; the ATL ice-storm
  trips of 10 Jan (AA 3104, WN 864) are thin (distances 25.6 and 15.7), as with embeddings: no earlier
  ice day at ATL (Finding 3).
- The page says what is compared, in plain words; distances are in Technical details.
- Embeddings are still built (`python -m murphy.pastdays`) so the comparison can be rerun.
