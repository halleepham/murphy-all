// The map tab (0025). Every number comes from /api/map and /api/trip; this file only draws.
// Layers: route + alternatives timeline (always), regions, linked airports, weather; a slider over
// the 24 hours up to the forecast hour. Forecasts only, never what happened.

const US = fetch("https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json").then(r => r.json());
const mapCache = {};  // by lead time: the layers do not depend on the deadline
const mapView = { regions: true, links: true, weather: true, hour: null, playing: null };
const VERDICT_COLOR = { keep: "--good", too_uncertain: "--warn" };  // anything else is --bad

async function map(box) {
  box.replaceChildren(el("p", "Drawing the map...", "muted"));
  const lead = $("lead").value;
  let d, us;
  try { [d, us] = await Promise.all([mapCache[lead] ||= get("/api/map?" + new URLSearchParams({ flight_id: flightId, lead_h: lead })), US]); }
  catch (e) { delete mapCache[lead]; box.replaceChildren(el("p", e.message || "The map could not load.", "error")); return; }
  if (tab !== "map") return;
  const last = d.hours_utc.length - 1;
  if (mapView.hour == null || mapView.hour > last) mapView.hour = last;

  const toggles = el("div", null, "controls map-toggles");
  [["regions", "Regions"], ["links", "Linked airports"], ["weather", "Weather"]].forEach(([k, label]) => {
    const l = el("label", null, "chip"), c = el("input"); c.type = "checkbox"; c.checked = mapView[k];
    c.onchange = () => { mapView[k] = c.checked; draw(); };
    l.append(c, " " + label); toggles.append(l);
  });
  const slider = el("input"); Object.assign(slider, { type: "range", min: 0, max: last, step: 1, value: mapView.hour });
  const hourLabel = el("span", null, "small"), play = el("button", "Play", "btn small");
  slider.oninput = () => { mapView.hour = +slider.value; draw(); };
  play.type = "button";
  play.onclick = () => {
    if (mapView.playing) { clearInterval(mapView.playing); mapView.playing = null; play.textContent = "Play"; return; }
    if (mapView.hour === last) mapView.hour = 0;
    play.textContent = "Pause";
    mapView.playing = setInterval(() => {
      if (tab !== "map" || mapView.hour >= last) { clearInterval(mapView.playing); mapView.playing = null; play.textContent = "Play"; return; }
      mapView.hour++; slider.value = mapView.hour; draw();
    }, 500);
  };
  const time_row = el("div", null, "map-slider"); time_row.append(play, slider, hourLabel);

  const svgBox = el("div", null, "map-box"), side = el("div", null, "map-side");
  const grid = el("div", null, "map-grid"); grid.append(svgBox, side);
  const timeline = el("div"), notes = el("div");
  box.replaceChildren(toggles, time_row, grid, timeline, notes);

  // --- base map, drawn once per open -----------------------------------------------------------
  const W = 900, H = 540, proj = d3.geoAlbersUsa().scale(1150).translate([W / 2, H / 2]), path = d3.geoPath(proj);
  const svg = d3.select(svgBox).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
    .attr("aria-label", `Map of ${trip.flight.origin} to ${trip.flight.dest} with regions and linked airports`);
  svg.append("path").datum(topojson.mesh(us, us.objects.states, (a, b) => a !== b)).attr("class", "state-lines").attr("d", path);
  svg.append("path").datum(topojson.feature(us, us.objects.nation)).attr("class", "nation").attr("d", path);
  const xy = a => a && proj([a.lon, a.lat]);
  const placed = d.airports.filter(a => xy(a)), offMap = d.airports.length - placed.length;
  const gLinks = svg.append("g"), gDots = svg.append("g"), gRoute = svg.append("g"), gLabels = svg.append("g");

  const risks = d.regions.flatMap(r => r.risk).filter(v => v != null);
  const color = d3.scaleSequential(d3.interpolateOrRd).domain([0, d3.max(risks) || 1]);
  const region = Object.fromEntries(d.regions.map(r => [r.community, r]));
  const at = (arr, h) => arr ? arr[h] : null;

  const o = d.route.origin, dst = d.route.dest, vcol = css(VERDICT_COLOR[trip.answer.verdict] || "--bad");
  if (xy(o) && xy(dst)) gRoute.append("path").datum({ type: "LineString", coordinates: [[o.lon, o.lat], [dst.lon, dst.lat]] })
    .attr("d", path).attr("class", "route").attr("stroke", vcol);
  [o, dst].forEach(a => { const p = xy(a); if (!p) return;
    gRoute.append("circle").attr("cx", p[0]).attr("cy", p[1]).attr("r", 7).attr("fill", vcol).attr("class", "end");
    gRoute.append("text").attr("x", p[0] + 10).attr("y", p[1] - 8).attr("class", "end-label").text(a.airport); });

  function draw() {
    const h = mapView.hour;
    hourLabel.textContent = `${d.hours_utc[h].slice(0, 16)} UTC` + (h === last ? " (the forecast hour)" : ` (${last - h} h before the forecast hour)`);

    gDots.selectAll("circle").data(placed, a => a.airport).join("circle")
      .attr("cx", a => xy(a)[0]).attr("cy", a => xy(a)[1]).attr("r", a => a.big ? 4 : 2.5)
      .attr("fill", a => { const v = at(region[a.community]?.risk, h); return mapView.regions && v != null ? color(v) : css("--line"); })
      .attr("stroke", css("--surface")).attr("stroke-width", .6)
      .selectAll("title").data(a => [a]).join("title")
      .text(a => { const g = at(d.gcn[a.airport], h), r = at(region[a.community]?.risk, h);
        return `${a.airport} ${a.name}\nRegion ${a.community}: ${r == null ? "no score" : pct(r)} predicted late, next 3 h` +
               (g == null ? "\nNot a big airport: no own score" : `\nThis airport: ${pct(g)} predicted late, next 3 h`); });

    const lk = d.links, top = new Set(lk.top_by_gcn[h] || []), op = xy(o);
    const nb = mapView.links && op ? lk.neighbors.filter(n => xy(d.airports.find(a => a.airport === n.airport))) : [];
    const pos = n => xy(d.airports.find(a => a.airport === n.airport));
    gLinks.selectAll("line").data(nb, n => n.airport).join("line")
      .attr("x1", op?.[0]).attr("y1", op?.[1]).attr("x2", n => pos(n)[0]).attr("y2", n => pos(n)[1])
      .attr("class", n => top.has(n.airport) ? "link top" : "link").attr("stroke-width", n => 0.5 + 2 * n.weight);
    gLabels.selectAll("text").data(nb.filter(n => top.has(n.airport)), n => n.airport).join("text")
      .attr("x", n => pos(n)[0] + 6).attr("y", n => pos(n)[1] + 4).attr("class", "link-label")
      .text(n => `${n.airport} ${pct(at(n.gcn, h))}`);

    renderSide(h);
  }

  function renderSide(h) {
    const out = [];
    if (mapView.regions) {
      out.push(el("h3", "Regions"), el("p", "Predicted late share of departures in the next 3 hours, averaged over each region's big airports.", "muted small"));
      const t = el("table"), hr = el("tr"); ["Region", "Predicted", "Airports scored"].forEach(x => hr.append(el("th", x))); t.append(hr);
      [...d.regions].sort((a, b) => (at(b.risk, h) ?? -1) - (at(a.risk, h) ?? -1)).forEach(r => {
        const tr = el("tr"), sw = el("span", null, "swatch"), v = at(r.risk, h);
        sw.style.background = v == null ? css("--line") : color(v);
        const c0 = el("td"); c0.append(sw, ` ${r.community}`);
        tr.append(c0, el("td", v == null ? "no score" : pct(v)), el("td", `${r.airports_scored} of ${r.airports}`)); t.append(tr);
      });
      out.push(t);
    }
    if (mapView.links) {
      out.push(el("h3", `Linked to ${trip.flight.origin}`));
      if (d.links.limited) out.push(el("p", d.links.reason, "muted small"));
      else {
        out.push(el("p", `Likely to go bad next (GCN, top 3): ${(d.links.top_by_gcn[h] || []).join(", ") || "none scored"}.`, "small"));
        out.push(el("p", `Strongest links, the simpler order: ${d.links.top_by_weight.join(", ")}. ${d.uncertainty.gcn_order}`, "muted small"));
      }
    }
    if (mapView.weather) {
      out.push(el("h3", "Weather at forecast time"));
      [d.weather.origin, d.weather.dest].forEach(w => {
        if (w.limited) { out.push(el("p", w.reason, "muted small")); return; }
        out.push(el("p", w.airport, "small strong"));
        out.push(el("pre", w.metar ? `METAR ${w.metar.text}` : "No observation in the last 3 hours.", "wx"));
        out.push(el("pre", w.taf ? `TAF issued ${w.taf.issued_utc} UTC\n` + w.taf.lines.join("\n") : "No TAF issued in the data window.", "wx"));
      });
    }
    side.replaceChildren(...out);
  }

  renderTimeline(timeline);
  const lim = [...d.uncertainty.limits]; if (offMap) lim.push(`${offMap} airports fall outside the map's projection and are not drawn.`);
  const p = d.provenance;
  notes.replaceChildren(sources("Where the map's numbers came from", `GCN: ${p.gcn}. Regions: ${p.regions}. Links: ${p.links}.`,
    `Forecast as of ${p.forecast_as_of_utc} UTC; the slider's last hour is ${p.forecast_hour_utc} UTC. Decision record ${p.decisions.join(", ")}.`,
    ...lim));
  draw();
}

// --- Alternatives as a timeline beside the route (0025): same route, so a bar per flight in time.
function renderTimeline(box) {
  const f = trip.flight, rows = [{ ...f, original: true }, ...trip.alternatives.filter(a => a.schedule_ok)];
  const bad = trip.alternatives.length - rows.length + 1;
  const out = [el("h3", "Your flight and the alternatives, by scheduled time")];
  if (rows.length === 1) out.push(el("p", trip.answer.verdict === "keep" ? "No change suggested, so no alternatives are listed." : "No alternative within your limits.", "muted small"));
  const t = s => new Date(s.replace(" ", "T") + "Z");
  const deadline = new Date(+t(f.arrives_utc) + 60000 * +$("deadline").value);
  const W = 900, rowH = 22, top = 24, H = top + rowH * rows.length + 8, left = 110, right = 20;
  const x = d3.scaleUtc().domain([d3.min(rows, r => t(r.departs_utc)), d3.max([deadline, ...rows.map(r => t(r.arrives_utc))])]).nice()
    .range([left, W - right]);
  const svg = d3.create("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("class", "timeline");
  svg.append("g").attr("transform", `translate(0,${top - 4})`).call(d3.axisTop(x).ticks(8).tickFormat(d3.utcFormat("%H:%M"))).attr("class", "axis");
  svg.append("line").attr("x1", x(deadline)).attr("x2", x(deadline)).attr("y1", top - 4).attr("y2", H).attr("class", "deadline");
  const nearEnd = x(deadline) > W - right - 90;  // keep the label inside the box
  svg.append("text").attr("x", x(deadline) + (nearEnd ? -4 : 4)).attr("y", H - 4).attr("text-anchor", nearEnd ? "end" : "start")
    .attr("class", "small-label").text("your deadline");
  const detail = el("p", "Click a bar for its details.", "muted small");
  rows.forEach((r, i) => {
    const y = top + i * rowH, g = svg.append("g").attr("class", "bar-row").style("cursor", "pointer");
    g.append("text").attr("x", left - 8).attr("y", y + 14).attr("text-anchor", "end").attr("class", "small-label").text(r.original ? `${r.flight} (yours)` : r.flight);
    g.append("rect").attr("x", x(t(r.departs_utc))).attr("y", y + 3).attr("height", rowH - 6).attr("rx", 3)
      .attr("width", Math.max(2, x(t(r.arrives_utc)) - x(t(r.departs_utc))))
      .attr("class", r.original ? "bar mine" : r.best ? "bar best" : r.gain > 0 ? "bar better" : "bar worse");
    g.on("click", () => detail.textContent = r.original
      ? `${r.flight}, yours: departs ${time(r.departs_local)}, arrives ${time(r.arrives_local)} local. Chance of making your deadline ${pct(trip.answer.chance)}.`
      : `${r.flight} on ${r.date}: departs ${time(r.departs_local)}, arrives ${time(r.arrives_local)} local. Chance ${pct(r.chance)} (${r.gain >= 0 ? "+" : ""}${(100 * r.gain).toFixed(0)} pts vs yours)${r.best ? ", the best option" : ""}.`);
  });
  out.push(svg.node(), detail, el("p", "Times on the axis are UTC. Green: better chance than yours (dark: the best). Grey: not better." +
    (bad ? ` ${bad} alternative${bad > 1 ? "s are" : " is"} not drawn: the source schedule arrives before it leaves.` : ""), "muted small"));
  box.replaceChildren(...out);
}
