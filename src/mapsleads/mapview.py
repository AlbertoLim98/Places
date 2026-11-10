import json
import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any

from . import storage
from .domain import CANDIDATE, DEAD_SITE, GUESSED_SITE, HAS_SITE, NO_SITE, ONLY_SOCIAL

# verdict -> (label, colour); order is the legend order.
STYLE: dict[str, tuple[str, str]] = {
    NO_SITE: ("Senza sito (confermato)", "#d62728"),
    ONLY_SOCIAL: ("Solo social", "#ff7f0e"),
    DEAD_SITE: ("Sito non raggiungibile", "#9467bd"),
    CANDIDATE: ("Da verificare", "#1f77b4"),
    GUESSED_SITE: ("Sito probabile (da controllare)", "#2ca02c"),
    HAS_SITE: ("Ha un sito", "#7f7f7f"),
}

TEMPLATE = """<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
html, body, #map { height: 100%; margin: 0; }
.legend { background: #fff; color: #222; padding: 8px 10px; border-radius: 6px;
  box-shadow: 0 1px 5px rgba(0,0,0,.4); font: 13px/1.5 system-ui, sans-serif; }
.legend label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.legend .dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block;
  border: 1px solid rgba(0,0,0,.4); }
.legend h4 { margin: 0 0 4px; font-size: 13px; }
.pop b { font-size: 14px; }
</style></head><body><div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const STYLE = __STYLE__;
const DATA = __DATA__;
const map = L.map("map");
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(map);

function popup(p) {
  const d = document.createElement("div"); d.className = "pop";
  const add = (t, bold) => { if (!t) return;
    const e = document.createElement(bold ? "b" : "div"); e.textContent = t; d.append(e); };
  add(p.name, true); add(p.category); add(p.address); add(p.phone);
  add(STYLE[p.verdict] ? STYLE[p.verdict][0] : p.verdict);
  if (p.detail) {
    const href = /^https?:\\/\\//i.test(p.detail) ? p.detail : "http://" + p.detail;
    const a = document.createElement("a"); a.href = href; a.textContent = p.detail;
    a.target = "_blank"; a.rel = "noopener noreferrer"; d.append(a);
  }
  return d;
}

const layers = {}, counts = {};
for (const v of Object.keys(STYLE)) { layers[v] = L.layerGroup().addTo(map); counts[v] = 0; }
const pts = [];
for (const p of DATA) {
  const s = STYLE[p.verdict]; if (!s) continue;
  counts[p.verdict]++; pts.push([p.lat, p.lon]);
  L.circleMarker([p.lat, p.lon], { radius: 7, color: "#222", weight: 1,
    fillColor: s[1], fillOpacity: 0.9 }).bindPopup(() => popup(p)).addTo(layers[p.verdict]);
}
if (pts.length) map.fitBounds(pts, { padding: [30, 30] }); else map.setView([45.4642, 9.19], 12);

const legend = L.control({ position: "topright" });
legend.onAdd = () => {
  const box = L.DomUtil.create("div", "legend");
  L.DomEvent.disableClickPropagation(box);
  const h = document.createElement("h4");
  h.textContent = "Esito (" + pts.length + ")"; box.append(h);
  for (const [v, s] of Object.entries(STYLE)) {
    if (!counts[v]) continue;
    const l = document.createElement("label");
    const c = document.createElement("input"); c.type = "checkbox"; c.checked = true;
    c.onchange = () => c.checked ? layers[v].addTo(map) : map.removeLayer(layers[v]);
    const dot = document.createElement("span"); dot.className = "dot"; dot.style.background = s[1];
    l.append(c, dot, document.createTextNode(s[0] + " (" + counts[v] + ")")); box.append(l);
  }
  return box;
};
legend.addTo(map);
</script></body></html>
"""


def _safe_json(obj: Any) -> str:
    # Keep names/URLs from closing the <script> block.
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")


def render(records: Iterable[Mapping[str, Any]], title: str = "Attività senza sito") -> str:
    data = [
        {k: r.get(k) or "" for k in ("name", "category", "address", "phone", "verdict", "detail")}
        | {"lat": float(r["lat"]), "lon": float(r["lon"])}
        for r in records
        if r.get("lat") is not None and r.get("lon") is not None
    ]
    style = {v: [label, colour] for v, (label, colour) in STYLE.items()}
    return (
        TEMPLATE.replace("__TITLE__", title.replace("<", "&lt;"))
        .replace("__STYLE__", _safe_json(style))
        .replace("__DATA__", _safe_json(data))
    )


def records_from_db(con: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in storage.all_rows(con) if r["verdict"]]


def write(con: sqlite3.Connection, path: str) -> int:
    records = records_from_db(con)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(records))
    return len(records)
