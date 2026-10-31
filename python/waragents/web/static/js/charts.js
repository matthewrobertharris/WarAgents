// Small SVG charts for the Analytics screen.
//
// They follow a few fixed rules so every chart reads the same way: one y-axis per chart, bars no
// thicker than 20px with a rounded end at the value and a square end at the baseline, a 2px gap
// between touching segments, 2px lines, quiet hairline grids, and text in text colours (a series'
// colour only ever marks a bar, line or legend key). Series colours are CSS variables (--series-1,
// --series-2, --seq-*) set in style.css for light and dark, and checked for colour-blind safety.
//
// Every chart redraws to fit its box when the box changes size, shows its numbers in a tooltip on
// hover and keyboard focus, and has a table view (chartCard) so nothing depends on hovering.

import { h } from "./dom.js";

const SVG = "http://www.w3.org/2000/svg";
const ROW = 30; // height of one row of horizontal bars
const BAR = 16; // bar thickness
const FONT = 12;

export const compact = (n) => {
  if (n === null || n === undefined) return "–";
  const abs = Math.abs(n);
  if (abs >= 1e6) return `${(n / 1e6).toFixed(abs >= 1e7 ? 0 : 1)}M`;
  if (abs >= 1e3) return `${(n / 1e3).toFixed(abs >= 1e4 ? 0 : 1)}K`;
  if (Number.isInteger(n)) return String(n);
  return String(Number(n.toFixed(abs < 10 ? 2 : 1)));
};
export const percent = (rate) => (rate === null || rate === undefined ? "–" : `${Math.round(rate * 100)}%`);

// An SVG element. Children are elements or text.
function s(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined && value !== false) node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// A bar from (x, y), w wide and t thick, rounded (4px) only at its value end.
function barPath(x, y, w, t, rounded) {
  const r = rounded ? Math.min(4, w / 2, t / 2) : 0;
  return `M${x},${y}h${w - r}${r ? `a${r},${r} 0 0 1 ${r},${r}` : ""}v${t - 2 * r}`
    + `${r ? `a${r},${r} 0 0 1 ${-r},${r}` : ""}h${-(w - r)}z`;
}

// The same, standing up: a column from the baseline at y + t up to y.
function columnPath(x, y, w, t, rounded) {
  const r = rounded ? Math.min(4, w / 2, t / 2) : 0;
  return `M${x},${y + t}v${-(t - r)}${r ? `a${r},${r} 0 0 1 ${r},${-r}` : ""}h${w - 2 * r}`
    + `${r ? `a${r},${r} 0 0 1 ${r},${r}` : ""}v${t - r}z`;
}

// Clean tick values from 0 to at least max.
function ticks(max, count = 4) {
  if (!(max > 0)) return [0, 1];
  const rough = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((m) => m >= rough);
  const out = [];
  for (let v = 0; v < max + step / 2; v += step) out.push(Number(v.toFixed(6)));
  if (out[out.length - 1] < max) out.push(out[out.length - 1] + step);
  return out;
}

// Shorten text to roughly fit a width (system-ui at 12px is about 6.6px a character).
function fit(text, width) {
  const chars = Math.max(3, Math.floor(width / 6.6));
  return text.length > chars ? `${text.slice(0, chars - 1)}…` : text;
}

// ---- the tooltip ----------------------------------------------------------------------------

let tipNode = null;

// rows: [{ value, label, series }], where series picks the key's colour (1 or 2), or none.
function showTip(event, title, rows) {
  tipNode ??= document.body.appendChild(h("div", { class: "chart-tip", role: "tooltip" }));
  tipNode.replaceChildren(
    title ? h("div", { class: "tip-title" }, title) : null,
    ...rows.map((r) => h("div", { class: "tip-row" },
      r.series ? h("span", { class: `tip-key series-${r.series}` }) : h("span", { class: "tip-key none" }),
      h("strong", {}, r.value), " ", h("span", {}, r.label))),
  );
  tipNode.hidden = false;
  let x;
  let y;
  if (event.type === "focus") {
    const box = event.target.getBoundingClientRect();
    x = box.left + box.width / 2;
    y = box.top;
  } else {
    x = event.clientX;
    y = event.clientY;
  }
  const { width, height } = tipNode.getBoundingClientRect();
  tipNode.style.left = `${Math.min(window.innerWidth - width - 8, Math.max(8, x + 14))}px`;
  tipNode.style.top = `${Math.max(8, y - height - 12)}px`;
}

function hideTip() {
  if (tipNode) tipNode.hidden = true;
}

// Show a tooltip on hover and keyboard focus of node.
function tipOn(node, title, rows) {
  const show = (e) => showTip(e, typeof title === "function" ? title() : title, typeof rows === "function" ? rows() : rows);
  node.addEventListener("pointermove", show);
  node.addEventListener("focus", show);
  node.addEventListener("pointerleave", hideTip);
  node.addEventListener("blur", hideTip);
}

// ---- pieces ---------------------------------------------------------------------------------

// A box that draws its chart to fit its width, and again when that changes.
function responsive(draw, className = "chart") {
  const box = h("div", { class: className });
  let width = 0;
  const redraw = () => {
    const now = Math.floor(box.clientWidth);
    if (now && now !== width) {
      width = now;
      box.replaceChildren(draw(width));
    }
  };
  new ResizeObserver(redraw).observe(box);
  return box;
}

// Keys for two or more series. kind is "bar" (a square) or "line" (a short stroke).
export function legend(series, kind = "bar") {
  return h("div", { class: "legend" }, series.map((item) => h("span", { class: "legend-item" },
    h("span", { class: `legend-key ${kind} series-${item.series}` }), item.label)));
}

// A card with a title, an optional legend and note, and the chart, which can be swapped for a
// table of the same numbers.
export function chartCard({ title, note, legendFor, chart, table, wide = false, empty = null }) {
  let showTable = false;
  const body = h("div", { class: "chart-body" });
  const toggle = h("button", {
    class: "small ghost", type: "button", "aria-pressed": "false",
    onclick: () => {
      showTable = !showTable;
      toggle.textContent = showTable ? "Chart" : "Table";
      toggle.setAttribute("aria-pressed", String(showTable));
      draw();
    },
  }, "Table");
  const draw = () => body.replaceChildren(empty ?? (showTable ? table() : chart()));
  draw();
  return h("section", { class: `card chart-card${wide ? " wide" : ""}` },
    h("div", { class: "chart-head" }, h("h2", {}, title), empty ? null : toggle),
    note ? h("p", { class: "hint chart-note" }, note) : null,
    empty ? null : legendFor ?? null,
    body);
}

// A plain table: columns are [heading, (row) => cell, numeric?].
export function dataTable(rows, columns) {
  return h("div", { class: "table-wrap" }, h("table", { class: "data" },
    h("thead", {}, h("tr", {}, columns.map(([heading, , num]) => h("th", { class: num ? "num" : "" }, heading)))),
    h("tbody", {}, rows.map((row) => h("tr", {}, columns.map(([, cell, num]) => h("td", { class: num ? "num" : "" }, cell(row))))))));
}

// ---- horizontal stacked bars ----------------------------------------------------------------

// One row per item, each a bar split into segments (one per series). Rows are clickable when
// onSelect is given, and the selected one is marked.
//   rows      [{ key, label, ... }]
//   series    [{ key, label, series: 1 | 2 }]: row[key] is the segment's size
//   end       (row) => the text after the bar, such as "67% of 12"
//   tip       (row) => tooltip rows
export function stackedBars({ rows, series, end, tip, selected = null, onSelect = null, actionLabel = "Filter by" }) {
  return responsive((width) => {
    const labelWidth = Math.min(180, Math.round(width * 0.32));
    const endWidth = 92;
    const plot = Math.max(40, width - labelWidth - endWidth - 12);
    const max = Math.max(1, ...rows.map((row) => series.reduce((sum, item) => sum + (row[item.key] ?? 0), 0)));
    const height = rows.length * ROW + 4;
    const svg = s("svg", { width, height, viewBox: `0 0 ${width} ${height}`, class: "bars", role: "list" });
    rows.forEach((row, i) => {
      const y = i * ROW + 2;
      const barY = y + (ROW - BAR) / 2;
      const isSelected = selected !== null && row.key === selected;
      const group = s("g", {
        class: `bar-row${onSelect ? " clickable" : ""}${isSelected ? " selected" : ""}`, role: "listitem",
        tabindex: onSelect ? "0" : null,
        "aria-label": `${row.label}: ${end(row)}${onSelect ? `. ${isSelected ? "Selected" : `${actionLabel} this`}` : ""}`,
      });
      group.append(s("rect", { class: "row-hit", x: 0, y, width, height: ROW, rx: 6 }));
      group.append(s("text", { class: "row-label", x: labelWidth - 8, y: y + ROW / 2, "text-anchor": "end",
        "dominant-baseline": "central", "font-size": FONT }, fit(row.label, labelWidth - 12)));
      const parts = series.map((item) => ({ item, value: row[item.key] ?? 0 })).filter((p) => p.value > 0);
      let x = labelWidth;
      parts.forEach((part, n) => {
        const w = (part.value / max) * plot;
        const last = n === parts.length - 1;
        const gap = last ? 0 : Math.min(2, w / 2);
        group.append(s("path", { class: `series-${part.item.series}`, d: barPath(x, barY, Math.max(1, w - gap), BAR, last) }));
        x += w;
      });
      if (!parts.length) group.append(s("rect", { class: "baseline-tick", x: labelWidth, y: barY, width: 1, height: BAR }));
      group.append(s("text", { class: "row-end", x: x + 8, y: y + ROW / 2, "dominant-baseline": "central", "font-size": FONT }, end(row)));
      if (onSelect) {
        group.addEventListener("click", () => onSelect(row));
        group.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect(row);
          }
        });
      }
      tipOn(group, row.label, () => tip(row));
      svg.append(group);
    });
    return svg;
  });
}

// ---- columns over time ------------------------------------------------------------------------

// Stacked columns, one per point in time, on one count axis.
//   points  [{ label, ... }], series as for stackedBars, tip (point) => tooltip rows
export function stackedColumns({ points, series, tip, onSelect = null }) {
  return responsive((width) => {
    const height = 200;
    const left = 34;
    const bottom = 22;
    const top = 8;
    const plotW = width - left - 4;
    const plotH = height - top - bottom;
    const totals = points.map((p) => series.reduce((sum, item) => sum + (p[item.key] ?? 0), 0));
    const yTicks = ticks(Math.max(1, ...totals));
    const yMax = yTicks[yTicks.length - 1];
    const band = plotW / Math.max(1, points.length);
    const colW = Math.max(3, Math.min(20, band * 0.6));
    const svg = s("svg", { width, height, viewBox: `0 0 ${width} ${height}`, class: "columns" });
    for (const t of yTicks) {
      const y = top + plotH - (t / yMax) * plotH;
      svg.append(s("line", { class: t ? "grid" : "axis", x1: left, x2: width - 4, y1: y, y2: y }));
      svg.append(s("text", { class: "tick", x: left - 6, y, "text-anchor": "end", "dominant-baseline": "central", "font-size": 11 }, compact(t)));
    }
    const labelEvery = Math.max(1, Math.ceil(points.length / Math.max(1, Math.floor(plotW / 64))));
    points.forEach((point, i) => {
      const cx = left + band * i + band / 2;
      const group = s("g", { class: `column${onSelect ? " clickable" : ""}`, tabindex: "0",
        "aria-label": `${point.label}: ${tip(point).map((r) => `${r.value} ${r.label}`).join(", ")}` });
      group.append(s("rect", { class: "row-hit", x: cx - band / 2, y: top, width: band, height: plotH }));
      let base = top + plotH;
      const parts = series.map((item) => ({ item, value: point[item.key] ?? 0 })).filter((p) => p.value > 0);
      parts.forEach((part, n) => {
        const hgt = (part.value / yMax) * plotH;
        const last = n === parts.length - 1;
        const gap = last ? 0 : Math.min(2, hgt / 2);
        group.append(s("path", { class: `series-${part.item.series}`, d: columnPath(cx - colW / 2, base - hgt + gap, colW, Math.max(1, hgt - gap), last) }));
        base -= hgt;
      });
      if (i % labelEvery === 0) {
        svg.append(s("text", { class: "tick", x: cx, y: height - 6, "text-anchor": "middle", "font-size": 11 }, point.label));
      }
      if (onSelect) group.addEventListener("click", () => onSelect(point));
      tipOn(group, point.label, () => tip(point));
      svg.append(group);
    });
    return svg;
  });
}

// ---- lines over turns -----------------------------------------------------------------------

// One or two series over a shared numeric x, on one axis. A hairline follows the pointer to the
// nearest x, with a tooltip of every series there. A null value is a gap in its line.
//   xs        the x values
//   lines     [{ label, values, series: 1 | 2 }]
//   tip       (i) => tooltip rows for point i
export function lineChart({ xs, lines, tip, xLabel = (x) => x, yFormat = compact }) {
  return responsive((width) => {
    const height = 180;
    const left = 40;
    const bottom = 22;
    const top = 10;
    const plotW = width - left - 10;
    const plotH = height - top - bottom;
    const all = lines.flatMap((l) => l.values).filter((v) => v !== null && v !== undefined);
    const yTicks = ticks(Math.max(1, ...all));
    const yMax = yTicks[yTicks.length - 1];
    const xMin = xs[0] ?? 0;
    const xMax = xs[xs.length - 1] ?? 1;
    const px = (x) => left + ((x - xMin) / Math.max(1, xMax - xMin)) * plotW;
    const py = (y) => top + plotH - (y / yMax) * plotH;
    const svg = s("svg", { width, height, viewBox: `0 0 ${width} ${height}`, class: "line-chart" });
    for (const t of yTicks) {
      svg.append(s("line", { class: t ? "grid" : "axis", x1: left, x2: width - 10, y1: py(t), y2: py(t) }));
      svg.append(s("text", { class: "tick", x: left - 6, y: py(t), "text-anchor": "end", "dominant-baseline": "central", "font-size": 11 }, yFormat(t)));
    }
    for (const t of ticks(xMax - xMin, Math.max(2, Math.floor(plotW / 80)))) {
      const x = xMin + t;
      if (x > xMax) break;
      svg.append(s("text", { class: "tick", x: px(x), y: height - 6, "text-anchor": "middle", "font-size": 11 }, xLabel(x)));
    }
    for (const line of lines) {
      // Runs of points without gaps, each drawn as its own path.
      const runs = [];
      line.values.forEach((v, i) => {
        if (v === null || v === undefined) return;
        if (i === 0 || line.values[i - 1] === null || line.values[i - 1] === undefined) runs.push([]);
        runs[runs.length - 1].push(`${px(xs[i]).toFixed(1)},${py(v).toFixed(1)}`);
      });
      for (const run of runs) {
        if (lines.length === 1) {
          const [first] = run[0].split(",");
          const [last] = run[run.length - 1].split(",");
          svg.append(s("path", { class: `area series-${line.series}`, d: `M${first},${py(0)}L${run.join("L")}L${last},${py(0)}z` }));
        }
        svg.append(s("path", { class: `line series-${line.series}`, d: `M${run.join("L")}` }));
      }
    }
    const cross = s("line", { class: "crosshair", y1: top, y2: top + plotH, visibility: "hidden" });
    const dots = lines.map((line) => s("circle", { class: `dot series-${line.series}`, r: 4, visibility: "hidden" }));
    svg.append(cross, ...dots);
    const hit = s("rect", { class: "row-hit", x: left, y: top, width: plotW, height: plotH, tabindex: "0",
      "aria-label": "Move along the lines with the arrow keys" });
    let current = xs.length - 1;
    const point = (i, event) => {
      if (!xs.length) return;
      current = Math.max(0, Math.min(xs.length - 1, i));
      const x = px(xs[current]);
      cross.setAttribute("x1", x);
      cross.setAttribute("x2", x);
      cross.setAttribute("visibility", "visible");
      lines.forEach((line, n) => {
        const v = line.values[current];
        dots[n].setAttribute("visibility", v === null || v === undefined ? "hidden" : "visible");
        if (v !== null && v !== undefined) {
          dots[n].setAttribute("cx", x);
          dots[n].setAttribute("cy", py(v));
        }
      });
      showTip(event, `Turn ${xs[current]}`, tip(current));
    };
    hit.addEventListener("pointermove", (e) => {
      const box = svg.getBoundingClientRect();
      const x = xMin + ((e.clientX - box.left - left) / plotW) * (xMax - xMin);
      let best = 0;
      xs.forEach((value, i) => { if (Math.abs(value - x) < Math.abs(xs[best] - x)) best = i; });
      point(best, e);
    });
    hit.addEventListener("focus", (e) => point(current, e));
    hit.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault();
        point(current + (e.key === "ArrowLeft" ? -1 : 1), { type: "focus", target: hit });
      }
    });
    const leave = () => {
      cross.setAttribute("visibility", "hidden");
      for (const dot of dots) dot.setAttribute("visibility", "hidden");
      hideTip();
    };
    hit.addEventListener("pointerleave", leave);
    hit.addEventListener("blur", leave);
    svg.append(hit);
    return svg;
  });
}

// ---- you against them ---------------------------------------------------------------------------

// Rows of paired bars, one pair per measure, each pair on its own scale (kills and damage aren't
// comparable, but your kills and theirs are). The values are printed beside the bars.
//   rows    [{ label, a, b, format? }]: a is series 1, b series 2
export function pairedBars({ rows, labels }) {
  return h("div", { class: "pairs", role: "table" },
    rows.map((row) => {
      const max = Math.max(row.a ?? 0, row.b ?? 0) || 1;
      const format = row.format ?? compact;
      const bar = (value, series) => h("div", { class: "pair-bar" },
        h("span", { class: "pair-track" },
          h("span", { class: `pair-fill series-${series}`, style: `width:${value ? Math.max(2, (100 * value) / max) : 0}%` })),
        h("span", { class: "pair-value" }, value === null || value === undefined ? "–" : format(value)));
      return h("div", { class: "pair-row", role: "row", "aria-label":
        `${row.label}: ${labels[0]} ${format(row.a)}, ${labels[1]} ${format(row.b)}` },
      h("div", { class: "pair-label" }, row.label),
      h("div", { class: "pair-bars" }, bar(row.a, 1), bar(row.b, 2)));
    }));
}

// ---- a share meter --------------------------------------------------------------------------

// A small horizontal meter for a share from 0 to 1, in the sequential ramp: the track is a light
// step of the same blue, so it reads as "how much" at a glance.
export function shareMeter(share) {
  return h("span", { class: "share-meter", "aria-hidden": "true" },
    h("span", { style: `width:${Math.max(share > 0 ? 3 : 0, Math.round(share * 100))}%` }));
}
