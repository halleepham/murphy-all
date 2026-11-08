# 0019 — GraphRAG (PLAN layer 5, part 2)

Date: 7 Nov 2026. Builds on `0018` Decision 2 (fixed queries; the LLM picks and explains,
code runs). **Nothing is built yet.**

## Decision 1 — How the traveler asks: suggested questions next to the trip

**AI recommended, owner accepted (option A, 7 Nov 2026).**

The screen shows a few questions beside the trip ("Why is this flight risky?", "Is there a
better flight?", ...). Each maps to one fixed query from `murphy/graph.py`. Answers are
predictable and testable, with fewer ways to fail.

**Alternative:** B, free text that the LLM maps to a query. More flexible, but the LLM can
pick the wrong query, which adds failure cases.

**Also rejected:** A+, suggested questions plus an "ask something else" box routed to the same
queries. AI proposed it because Challenge 3 says "accept natural-language questions". The
owner rejected it (7 Nov 2026): suggested questions only, and that line need not be met.

## Decision 2 — Compare GraphRAG with and without community information

**Owner required (Challenge 4 ablation).** The same questions answered twice: once with the
community and co-disruption neighbors in the retrieved rows, once without. Alongside the
`0018` baselines: no retrieval, and BM25 over the same facts as text.

## How it works (built 7 Nov 2026)

`murphy/graphrag.py`. A suggested question runs its fixed queries from `murphy/graph.py`. Code
tags each row `[E1]`, `[E2]`, ... and writes every number (chances as whole percents). The LLM,
Groq `openai/gpt-oss-120b` at temperature 0, explains the rows and cites tags. Code then checks the
answer: numbers not in the evidence, and tags that do not exist. An unknown flight stops before the
LLM is called.

| Question | Queries | Type |
|---|---|---|
| How likely is this flight to make me late? | `flight` | basic |
| Is there a better flight? | `alternatives` | traversal |
| Why is this flight at risk? | `why` + `taf` | multi-hop |
| How are other regions doing today? | `community_day` | analytics |

Compared four ways: **graph**; **graph without communities** (the `why` question only, the one
whose evidence has community information; `region` has no answer without them); **BM25** over the
same graph facts as sentences, top 10, no time or lead filter (`rank-bm25`); **no retrieval**.

`PYTHONPATH=. python scripts/graphrag_eval.py`. Cases: AA3104 ATL–DFW 10 Jan at 24 h (the example);
WN1385 SDF–MDW 6 Jan at 24 h (no weather reports at SDF); DL1725 ATL–GSP 10 Jan at 2 h (no
alternative); WN1383 MDW–RSW 12 Jan at 24 h (calm, low risk); a made-up flight. Output:
`data/graphrag/eval_run1.txt`, `eval_run2.txt`, `eval.jsonl` (not committed; `/data/`).

## Finding 1 — Run 1: the evidence was right, the LLM misread it

Read by AI from `eval_run1.txt`, before the revision:
- **Mixed-up chances.** AA3104 "Is there a better flight?": the rows had `p_miss` (the alternative)
  and `current_p_miss` (the trip). The answer gave every alternative 42%, the trip's value, and
  said there was no better flight. DL414 was at 16%.
- **A fixed weight read as today's risk.** "CLT 1.061 … indicating elevated risk". The weight is a
  2023–24 link, not current.
- **Decoded weather codes wrongly.** `19012G20KT` became "190 kt"; it is wind from 190° at 12 kt.
  The number check flagged it.
- **Refused a fair question.** "Chances of making it?" got "only p_miss is given": the model
  rightly did not compute 1 − p.

## AI recommendation — revise the evidence, not the model

**AI recommended and applied while building; owner accepted, 7 Nov 2026.**

- Rename `p_miss`/`current_p_miss` to `alt_p_miss`/`trip_p_miss` in the `alternatives` query.
- Send a short glossary of the fields in the evidence (`GLOSSARY`), written by code.
- Ask "How likely is this flight to make me late?", which the evidence answers directly.
- Add decoded METAR fields (temperature, wind, gust, visibility, weather codes) to `why`. Tell the
  LLM not to decode raw METAR/TAF numbers. TAFs stay raw: decoding them means reloading the graph.
- Drop co-disruption neighbors with no METAR: nothing about them is known at `as_of`.

**Alternative:** a larger or different model. Not tried: the evidence was ambiguous, so a better
reader would still be guessing.

## Finding 2 — Run 2: after the revision

Same cases, `eval_run2.txt`. 16 answers per system (4 flights × 4 questions); the made-up flight
returned "No record of this flight in the graph." without an LLM call. Counted by code:

| | Graph | Graph, no communities | BM25 | No retrieval |
|---|---|---|---|---|
| Answers | 16 | 4 (why only) | 16 | 16 |
| Cite evidence | 15 | 4 | 11 | 0 |
| Contain a number not in the evidence | 1 | 1 | 2 | 0 |
| Key fact present (trip's chance; best alternative) | 6 of 7 | – | 5 of 7 | 0 of 7 |
| Evidence holds facts not known at `as_of` | 0 | 0 | 12 | 0 |

Read by AI:
- **Graph** fixed run 1's mistakes: AA3104 now lists DL414 at 16% first. The one miss named
  WN1383's best alternative by time ("1010 am"), not by flight number. The one number: "15 000 ft",
  decoded from a METAR.
- **BM25** has no time or lead filter. On DL1725 at 2 h it offered alternatives from the 6 h
  forecast and said "a better flight exists"; at 2 h murphy offers none. For AA3104 it did not
  retrieve the trip's own forecast, nor any weather for "why". 12 of 16 evidence sets held outcomes
  learned after the flight; no answer was seen to use them.
- **No retrieval** never invented a number in run 2 and answered nothing. In run 1 it invented
  "4 inches of snow at SDF" with made-up tags.
- **With vs without communities** (`why`): on AA3104 and DL1725 both answers rest on ATL's weather;
  the community version named no neighbor in AA3104's case. On WN1385, where SDF has no weather,
  without communities the answer was "no information"; with them it cited BNA and ATL weather and
  overreached ("strongly linked airports are already seeing adverse weather" for BNA overcast at
  15,000 ft). On WN1383 the community version named none either.

**Limits:** 4 flights is a small sample; counts, not rates. "Key fact" is checked only where code
can name it. Whether an explanation is *right* is the owner's reading, not a code check. Decoded
numbers in "5 000"-style spacing are caught; other decodings may not be.

## Limitation — the larger evaluation was stopped by Groq's daily limit

**Owner decided, 7 Nov 2026: stop and state it as a limitation.**

The owner asked why only 4 flights. `scripts/graphrag_eval.py` now adds 27 flights picked by code:
3 per day over the 9 days, one each at low (under 20%), middle and high (50% or more) chance of
missing, with the lead and the pick set by md5 of the flight ID. 32 cases, 434 answers.

It stopped at Groq's free-tier limit for `openai/gpt-oss-120b`: 200,000 tokens per day (Groq's 429
message). About 189 answers were cached, covering the 5 cases above and most of 6 sampled flights; the rest
were not asked. So Finding 2 rests on 4 real flights and one made-up one. No sampled answer is
reported, and no answer was marked right or wrong by hand.

**What it means:** the counts above show how each system fails, not how often. The same limit caps
the deployed app at roughly 190 answers a day (`0005`).

**To finish later:** rerun the script; cached answers cost nothing and the run resumes. It fetches
all evidence first, because Aura dropped an idle connection while the run waited on Groq.
Then mark the graph answers (supported, incomplete, overreach, wrong, right or wrong refusal) and
have the owner check six.
