// Small helpers shared by every page.
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; };
const pct = x => (100 * x).toFixed(0) + "%";
const time = t => t ? t.slice(0, 2) + ":" + t.slice(2) : "?";

async function get(url) {
  const r = await fetch(url);
  const body = await r.json();
  if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  return body;
}
