# 0023 — App structure: landing, results with tabs, about (PLAN layers 6–7)

Date: 8 Nov 2026. **Built** (Decision 2). Code: `murphy/app/static/` (`index.html`, `trip.html`,
`about.html`, `app.css`, `common.js`), routes in `murphy/app/server.py`, test
`test_the_three_pages_and_shared_files_are_served` in `tests/test_app.py`.

## Human design

The owner wants it to feel like a real application, not a long single page:

- a top bar saying "Murphy" on every page (logo later);
- a landing page: headline and short description on the left with an About button, the flight
  form on the right with examples that prefill it; no accounts or logins;
- an About page about the project;
- a results page that opens with the flight the traveler entered, and tabs, because there is a
  lot to show. The owner asked the AI to structure the rest and will give feedback on the page.

## AI recommendation

Build the structure now and leave the look (colors, fonts, logo, headline, About text) to a
design pass at the end, so that the remaining features (the interactive chart, trip text, the
lead-time view, the map) each land in a known place instead of piling onto one page.

**Owner accepted**, 8 Nov 2026.

## Decisions

1. **Three plain HTML pages, no framework**: `/`, `/trip?flight_id=…`, `/about`, sharing one
   stylesheet and one helper script. The old page already took `?flight_id=`, so this split moved
   code rather than rewriting it.
2. **Results page, as the AI structured it** (owner to give feedback in the browser):
   - Card at the top: the flight (number, route, date, times), then the chance as one large
     number, the verdict in color, the track record in one line, and the lead-time and deadline
     controls.
   - Tabs: **Options** (alternatives; the earlier-departure limit and the sort live here),
     **Similar days**, **Rules** (the matching situation preselected, the others in a dropdown).
     A tab loads its data only when opened. (First build also had Ask and Sources & limits tabs;
     see Decisions 5–6.)
   - Notes and provenance sit behind "Sources" or "About the prices" links in each tab, so they
     are one click away rather than gone.
3. **Examples fill the form; the traveler still presses the button.** Examples the questions
   cover carry a "Q&A" tag.
4. **Chart.js for the interactive chart** (owner approved the dependency, 8 Nov 2026), loaded from
   a CDN at a pinned version, so nothing is installed. Alternatives: plain SVG (no dependency, but
   more code to own); Plotly or Vega-Lite (heavier than needed). Not yet used.

## Owner feedback on the first build, 8 Nov 2026 (layout and content only; look later)

5. **Ask is a sidebar on the right**, like an embedded assistant, and stays while the tabs change.
   The conversation clears whenever the trip reloads (lead time, deadline, earlier limit or sort),
   so an answer never sits beside settings it was not made for (AI choice). On narrow screens it
   drops below the tabs.
6. **No Sources & limits tab.** Limits move to the About page; a test checks the page holds every
   line of `LIMITS` in `server.py`. The forecast's own provenance (model, as-of time, flight
   record) is specific to the trip, so it stays on the results page as a "Where this forecast
   came from" link in the top card (AI choice, to keep Evidence + Provenance on every output).
7. **About page outline:** what Murphy does, why it is named Murphy (the owner writes this), how
   it works (the poster's diagrams later), data sources, limitations. A high-level version of the
   poster.
8. **Visualizations are still to come** in the tabs and the top card.

## Evidence

- `pytest -q`: 194 passed after the first build (193 before, plus the page test); 195 after the
  feedback (plus the limits test).
- App on port 8766: `/`, `/trip`, `/about`, `/static/app.css`, `/static/common.js` return 200;
  `node --check` passes on both pages' scripts.
- No API changed, so no number changed.

## Open

- Owner's feedback on the results page.
- Before the chart: whether the forecast supports any deadline, or only 30, 60 and 120 minutes.

## Change, 8 Nov 2026: Ask Murphy floats

**Owner:** the side panel should not have its own scroll and should give the main column more room;
asked whether it could fold sideways, or open from a floating button in the corner.
**AI:** all three are possible (fold sideways, floating button, or both by screen width); recommended
the floating button. **Owner chose the floating button.** The results page now uses the full width;
a round button at the bottom right opens Ask Murphy as a card over the page (× or Esc closes it).
Only the card's messages scroll, since an overlay cannot grow past the screen. Checked in headless
Chrome at 1400 and 500 px wide.

## Change, 8 Nov 2026: wider Ask panel, evidence as tables

**Owner:** make the open panel wider; format the evidence rows better, maybe a simple table.
Panel is now up to 600 px wide. Evidence is one table per graph query, with plain column names
(the glossary sent to the LLM, `graphrag.GLOSSARY`, is now returned with the answer and shown as the
header tooltip). Fields equal in every row are written once above the table; a single row is shown
as a two-column table. Source ids, "known at" times and the raw METAR sit in a tooltip on each [E]
tag, so every row stays traceable. Checked in headless Chrome on real evidence rows saved in
`data/graphrag/eval.jsonl`; no new Groq calls were made.

## Change, 8 Nov 2026: plain words first, detail folded

**Owner:** the weather and linked-airport text was hard to follow ("I don't really know what the
second sentence is"); show user-understandable labels and explanations, and hide technical detail in
a collapsible, across the whole app. **AI proposed** a rule for every section, with three choices;
**owner accepted all recommendations.**

- **Rule:** visible text answers the traveler in one or two plain sentences, with no model or
  data jargon (GCN, TAF, METAR, UTC, kt, link weight, decision numbers). "How to read this" folds
  explain what rows, colors and lines mean. "Technical details" folds keep the model, sources, raw
  reports, accuracy figures and decision records, so evidence and provenance stay on the page.
- **Choices:** wind in mph (knots only in the details); local times everywhere (UTC only in the
  details); areas named by their busiest airports ("ATL, MCO, MIA area"), from the Community nodes
  in Neo4j, exported by `scripts/export_links.py` to `community_busiest.parquet`.
- **Weather:** per airport, one line for the flight time ("Expected around then: low clouds (down to
  700 ft), freezing rain or drizzle, ice pellets") and one short "Right now" line; the full forecast
  and the original reports are folded.
- **Linked airports:** what a link means is stated; "Why these three?" says the `0022` result in
  plain words: 45% of the model's picks were among the 3 worst-hit linked airports, against 30% for
  the thickest lines and 29% for random.
- Also: "Past accuracy" instead of "Track record", "not tested" instead of "not checked", "Compared
  with yours: +52 points" instead of "Gain +52 pts"; similarity scores and passage hashes folded.
- Not changed: the similar-days sentences from `0020` still say "kt"; they are the text the search
  embeds, so rewording them means rebuilding that index.
