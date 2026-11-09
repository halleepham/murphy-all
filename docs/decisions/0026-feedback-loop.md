# 0026 — Human feedback on Ask Murphy answers (Challenge 4 Task 3)

Date: 8 Nov 2026. **Built.**

## Human design

The owner first thought the GenAI pieces were done, since GenAI had been used to build the app.

## AI recommendation and the owner's decision

**AI:** Challenge 4 asks for GenAI inside the application. Task 2 is covered by Ask Murphy
(conversational Q&A over the knowledge graph, `0019`) beside the deadline what-if (`0024`). Task 3's
loop ends "Human Validation and Feedback → Refined AI Response", and the app had no way for a
traveler to say an answer is wrong. Recommended a small feedback step. **Owner accepted**, on
condition that it uses few Groq credits and that the demo questions come first.

## What was built

- Under each answered question: "Looks right" or "Something's wrong" with a note (up to 300
  characters).
- **Looks right:** saved to `data/graphrag/feedback.jsonl` (gitignored). No LLM call.
- **Something's wrong:** one Groq call. The first answer is taken from the cache, not from the browser;
  the same evidence, that answer and the note go back to the model, which corrects the answer if
  the evidence supports the traveler and says so if it does not. The number check runs against the
  evidence only, so a number that appears only in the note is flagged. One correction per answer
  on the page; at most 20 a day (`MAX_REFINES_PER_DAY`). Every correction is logged with the first
  answer, the note, the new answer and its checks.
- **Groq order:** the 12 demo questions (3 example flights x 4) were cached first, then one real
  correction was run. Cache: 201 entries before, 209 after the demo questions, 210 after the test.
  The 7th demo call hit Groq's per-minute limit and was retried after a few seconds.

## Evidence

Real run, 8 Nov 2026, F9 4195 LGA-MIA, "How likely is this flight to make me late?", note "I think
the chance of being late is lower than that.": the model kept the 81% from E1 and said the evidence
does not support a lower chance; checks: no invented numbers, no bad tags.

Tests: `tests/test_app.py`, 4 cases with no Groq call: "right" is saved without an LLM call; "wrong"
returns a checked correction built from the first answer and the note, and a number only in the
note is flagged; a note is required and the daily cap holds; at the Groq limit it says so.

Found while caching the demo: WN 864 ATL-MCO "Why is this flight at risk?" says "06000 feet" for the
METAR's `OVC060`; the check flags it as not in the evidence. Left as is: it shows the check working.

## Not done

The feedback does not change later answers or the models; it is a record and a one-off correction.
