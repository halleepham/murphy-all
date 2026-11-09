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

## Change, 8 Nov 2026: "Why Murphy" written

From the owner's slide: Edward A. Murphy Jr. (aerospace engineer, Murphy's law) and Allan H. Murphy
(meteorologist and statistician, forecast quality vs value), connected to the app: forecast what
goes wrong, show how reliable past forecasts were, turn each into a decision. AI added one fact not on
the slide, to check: the 1949 rocket-sled tests at Edwards Air Force Base.

## Change, 8 Nov 2026: the styling pass

**Human design.** The owner disliked the dark mode (the app followed the Mac's dark setting) and
wanted something lighter, blue accents, and a look like a real application.

**AI recommendation.** Three light mockups, built as temporary style overrides and screenshotted:
A, a clean travel app (navy bar, bright blue, system font, soft shadows), **recommended**; B, a flight
board (IBM Plex Sans and Mono, sharp edges, a dark departure-board strip); C, calm editorial (cream,
serif headlines, slate blue).

**Owner's decision: modified.** B's fonts, sharp edges and logo on C's cream background, so the
page is warmer than B's cool gray. The departure-board strip is kept. Fonts are stored in the repo
(`static/fonts/`, IBM Plex 5.3.0 from `@fontsource`, latin subset, 160 KB, SIL OFL 1.1 in
`OFL.txt`) so the demo works offline. AI then warmed the grays (borders, secondary text) to match.

**Owner's further asks, all built:**
- Light only. Dark mode removed.
- The brand in the top bar lines up with the page content: one page width (`--page`) for the top
  bar, the content and the footer.
- About page at full width: sections as cards, with How it works, Data sources and Limitations side
  by side. Text unchanged.
- Results page sectioning: each tab is a stack of white cards with space between them, so the map,
  the weather and the alternatives read as separate sections.
- Tabs styled as folder tabs that sit on the panel below them.
- Drop-down arrows drawn by the page and set 14 px in from the edge.
- Owner asked whether "Your flight and the alternatives" belongs with the map. AI: no, it compares
  the alternatives, so it moved to the Options tab under the table. Its time zone still comes from
  the map's data, now fetched once and shared by both tabs.

Also added: a "how it works" strip and a footer on the landing page, a footer on every page, and
designed loading and error states. No numbers, wording rules or folds changed.

**Evidence.** Before and after screenshots of every page (headless Chrome with the Mac in dark
mode, 8 Nov). `pytest -q`: 222 passed.

**Owner's review of the styling, 8 Nov.** (1) No course name in the footer or on the About page; "How it works" there as one bullet per sentence. (2) The tab strip had its
own scroll bar: a bug. `overflow-x: auto` on the strip also clips vertically, and the active tab
sat 1 px taller. Fixed: the strip wraps instead of scrolling. (3) The deadline chart was confusing:
the deadline and the typical-flight curve were both dashed, and Chart.js drew the legend keys solid.
Fixed: the deadline is a solid line with a round handle, and the page draws the key itself, so the
dashes show and the deadline has its own entry ("Your deadline (drag to move)").
