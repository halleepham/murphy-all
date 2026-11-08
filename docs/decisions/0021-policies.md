# 0021 — Policy passages (PLAN layer 5, vector retrieval part 2)

Date: 7 Nov 2026. Builds on `0004` Decisions 3–4 and `0018` Decision 3. Status: collecting.

What the traveler gets: beside a forecast, the policy passages that apply to their airline and
situation (cancelled, long delay, missed connection, refund), each with its source, section and
the date it was collected. Code retrieves; the LLM may only explain a passage, never decide an
entitlement.

## Decision 1 — Sources: federal rules plus three contracts of carriage

**AI recommended, owner modified, 7 Nov 2026.**

- AI options: A, federal rules only; **B (recommended)**, federal rules plus one major carrier
  (Delta or United) and Frontier; C, every carrier in scope (`0004` Decision 1).
- **Owner chose B, modified:** Delta, United and Southwest, in that priority order, instead of
  one major carrier plus Frontier.
- **Effect:** the low-cost contrast in `0004` comes from Southwest rather than Frontier.
  Frontier's interline question (`0004` Decision 1) stays unverified.

## Collection, 7 Nov 2026

Raw files are in `private/policies/raw/` (gitignored: contract text is not committed, `0004`
Decision 3). Hashes are SHA-256 of the file as downloaded.

| Source | URL | Result | SHA-256 (first 12) |
|---|---|---|---|
| 14 CFR 260, refunds | eCFR API, `full/2026-11-05/title-14.xml?part=260` | 200, saved | `d79cfeb99842` |
| 14 CFR 259, customer service and tarmac delays | same, `part=259` | 200, saved | `5fc378fb41cd` |
| 14 CFR 250, oversales | same, `part=250` | 200, saved | `5dc3926a06ea` |
| Delta contract of carriage | delta.com/us/en/legal/contract-of-carriage-dgr | 200, HTML, 137 KB | `62aedb777843` |
| United contract of carriage | united.com/en/us/fly/contract-of-carriage.html | blocked: connection reset | — |
| Southwest contract of carriage | southwest.com/…/contract-of-carriage.pdf | 200, PDF, 801 KB | `e1a75b1ebfef` |
| DOT Customer Service Dashboard | transportation.gov/airconsumer/airline-customer-service-dashboard | blocked: 403 | — |

eCFR is current to 5 Nov 2026 (its `titles.json`). Sites that block scripted downloads are not
worked around; the owner can save those pages from a browser instead.

Owner, 7 Nov 2026: United is not needed; build with what was collected. The DOT dashboard is
not needed either: the federal rules themselves are the source. `pypdf` 7.0.0 approved (pure
Python wheel) to read the Southwest PDF.

Southwest's contract is the 59th revision, effective 6 Nov 2026 (its cover page).

## Decision 2 — Passages follow each source's own sections

**AI decided while building; within Decision 1.** A passage is one section as the source
numbers it: an eCFR section (`14 CFR 260.6`), a Delta rule's lettered part (`RULE 22 — A.
Involuntary Refunds`), a Southwest lettered part (`9. … — b. Southwest Cancellations …`). Each
long section is cut at paragraph breaks into windows of at most 220 words, labeled `part 2/4`,
because `bge-small` reads at most 512 tokens. Southwest headings come from the PDF's own table of
contents and must appear in that order, so body text cannot fake a heading; the build fails if
any is missing.

Built: `murphy/policies.py`, `python -m murphy.policies` → `private/policies/passages.parquet`.

| Carrier | Sections | Passages | Words |
|---|---|---|---|
| federal (14 CFR 250, 259, 260) | 32 | 69 | 10,833 |
| Delta | 39 | 82 | 11,907 |
| Southwest | 49 | 126 | 19,364 |

Passage length: 10 to 220 words, median 170. Found while checking: Delta's Rule 19 B heading is
105 characters and was first read as body text; the heading limit was raised to 140.
Tests: `tests/test_policies.py`, 6 cases.

## Decisions 3–5 — How it is searched, tested and shown

**AI recommended, owner accepted all three, 7 Nov 2026.**

3. **Search.** Code picks a situation; its fixed question is searched over the flight's airline
   plus the federal rules. Eight situations (`murphy.policies.SITUATIONS`). The first one shown
   follows the advice (`DEFAULT_SITUATION`: cancelled → cancelled, consider changing → switch
   flights myself, otherwise long delay); the traveler can pick any other. An airline without a
   collected contract gets the federal rules only, and the app says so. Rejected: free-text
   questions, which could not be tested in the same way.
4. **Test.** The 8 situations × Delta and Southwest = 16 pairs. AI marks the relevant sections
   before any search runs; the owner checks them. Embeddings vs BM25 vs random, on whether a
   relevant passage is in the top 3.
5. **App.** The top 3 passages, quoted as written, with section, link, collection date and file
   hash. No LLM summary for now: it would spend Groq budget and could misstate an entitlement.
   It may come in layer 6, checked against the quotes.

## Finding 1 — Embeddings find a relevant passage more often than BM25

`python scripts/policies_eval.py`, 7 Nov 2026 → `data/policies/eval.csv`. Marks are in the
script (`RELEVANT`), written before the first run.

| Method | Relevant passage in top 3 (of 16 pairs) |
|---|---|
| Embeddings (`bge-small`) | 13 (0.812) |
| BM25 | 8 (0.500) |
| Random 3 from the pool | 0.143 expected |

Paired: 6 pairs only embeddings hit, 1 only BM25 hit; exact sign test, two-sided p = 0.125. So
the gap is large but **not significant** on 16 pairs. Both beat random.

BM25 misses where the question's words differ from the contract's: "missed my connecting
flight" (first relevant rank 15 for Delta, 9 for Southwest), "sitting on the plane on the
runway" vs "tarmac" (5, 4), "switch to an earlier flight" vs "rerouting" (32, 21).

Embedding misses (top 3 shown in `eval.csv`):
- **Southwest, hotel or meals:** deliberate thin case. The contract says nothing on hotels or
  meals; only federal 259.5 and 259.9 could hit, at rank 24. BM25 reached a federal one at
  rank 2.
- **Southwest, schedule change:** first relevant at rank 4; the top 2 are 14 CFR 259.8
  (the airline must tell you of a change), which is related but states no options.
- **Southwest, switch flights myself:** first relevant at rank 5. **A marking error found after
  the run:** the top passage, `3. Fares — a` part 1/4, has a
  paragraph on changing a ticket and is relevant; the marks left it out. With that one mark added, embeddings hit
  14 of 16 (0.875) and BM25 stays at 8. The script keeps the marks as written; owner to check.

**Out of scope, deliberate:** three questions no policy answers (weather, lounges, driving
time). Their top embedding scores were 0.6215, 0.5189, 0.6701; the 16 in-scope top scores
ranged 0.6910–0.8312. A cutoff could separate these few, but it would be set on the same 19
questions, and the Southwest hotel case scores 0.7042 with nothing relevant. So no cutoff is
used. The app asks only the fixed situation questions, so out-of-scope questions do not arise
there.

**Owner to check:** the marks in `RELEVANT`, and the `3. Fares — a` correction.

## Limitation

When the airline's contract is silent (Southwest on hotels and meals), the app still shows the
three closest passages, none relevant, and nothing in the score warns of it. The quotes are
shown as written, so a reader can see that they do not answer the question, but the app does
not say so.

## Built

`murphy/policies.py` (search), `scripts/policies_eval.py`, `GET /api/policies` in
`murphy/app/server.py`, "What the rules say" on the page. Tests: `tests/test_policies.py` and
the policies tests in `tests/test_app.py`. Checked in the running app on 7 Nov 2026: Delta,
Southwest and United flights (United gets the federal-only note).
