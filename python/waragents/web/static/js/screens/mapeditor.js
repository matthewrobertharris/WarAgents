// Editing one map. The map grows from the dashed + cells around its edge, so it can be any
// shape. Select tiles by clicking or dragging, then change them from the toolbar under the map.
// Changes save themselves a moment after you stop, and Ctrl+Z / Ctrl+Y undo and redo.
//
// While editing, the map is kept as tiles keyed by "x,y". Its lowest x and y are always 0
// (normalise() shifts everything after a change), so the keys match the saved file.

import { get, put, reference } from "../api.js";
import { drawBoard } from "../board.js";
import { slotColour } from "../colours.js";
import { fill, h, showError } from "../dom.js";
import { describeCriterion } from "./newgame.js";

const MAX_DIRT = 15;
const MAX_FOOD = 100;
const DEFAULT_RATE = 10;
const MODES = {
  FIXED: "1 turn a second",
  CLICK: "2 turns a second",
  CONST: "25 turns a second",
};
const CRITERION_DEFAULTS = { turns: 300, amount: 50, exp: 10, dirt: 0, times: 5, x: 0, y: 0, action: "EAT" };

const key = (x, y) => `${x},${y}`;
const unkey = (k) => k.split(",").map(Number);
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const NEIGHBOURS = [[-1, 0], [1, 0], [0, -1], [0, 1]];

// ---- the map model -----------------------------------------------------------------

function fromJson(map) {
  const model = {
    name: map.name, mode: map.mode, maxAgents: map.maxAgents,
    criteria: structuredClone(map.criteria ?? []),
    tiles: new Map(), plants: new Map(), starts: new Map(),
  };
  map.dirt.forEach((row, y) => row.forEach((dirt, x) => {
    if (dirt !== null) model.tiles.set(key(x, y), { dirt, food: map.food[y][x] ?? 0 });
  }));
  for (const p of map.plants) model.plants.set(key(p.x, p.y), p.rate);
  for (const s of map.starts) model.starts.set(key(s.x, s.y), s.slot);
  return model;
}

function bounds(model) {
  const xs = [], ys = [];
  for (const k of model.tiles.keys()) {
    const [x, y] = unkey(k);
    xs.push(x);
    ys.push(y);
  }
  const minX = Math.min(...xs), minY = Math.min(...ys);
  return { minX, minY, width: Math.max(...xs) - minX + 1, height: Math.max(...ys) - minY + 1 };
}

function toJson(model) {
  const { width, height } = bounds(model);
  const grid = (attr) => Array.from({ length: height }, (_, y) =>
    Array.from({ length: width }, (_, x) => model.tiles.get(key(x, y))?.[attr] ?? null));
  return {
    name: model.name,
    mode: model.mode,
    maxAgents: model.maxAgents,
    dirt: grid("dirt"),
    food: grid("food"),
    plants: [...model.plants].map(([k, rate]) => { const [x, y] = unkey(k); return { x, y, rate }; }),
    starts: [...model.starts].map(([k, slot]) => { const [x, y] = unkey(k); return { slot, x, y }; }),
    criteria: structuredClone(model.criteria),
  };
}

// Shift everything so the lowest x and y are 0. Returns the shift, so the caller can move the
// selection too.
function normalise(model) {
  const { minX, minY } = bounds(model);
  if (minX === 0 && minY === 0) return [0, 0];
  const shift = (m) => new Map([...m].map(([k, v]) => { const [x, y] = unkey(k); return [key(x - minX, y - minY), v]; }));
  model.tiles = shift(model.tiles);
  model.plants = shift(model.plants);
  model.starts = shift(model.starts);
  for (const c of model.criteria) {
    if ("x" in c) {
      c.x -= minX;
      c.y -= minY;
    }
  }
  return [minX, minY];
}

const slotsOf = (model) => [...new Set(model.starts.values())].sort((a, b) => a - b);

// ---- the screen ------------------------------------------------------------------------

export async function mount(root, mapId, query) {
  const [saved, ref] = await Promise.all([get(`/api/catalogue/maps/${mapId}`), reference()]);
  if (saved.error) throw new Error(`This map can't be edited: ${saved.error}`);

  const ed = {
    model: fromJson(saved),
    problems: saved.problems ?? [],
    selection: new Set(),
    history: [],        // snapshots to undo to, oldest first
    future: [],         // snapshots to redo
    lastLabel: null,
    lastAt: 0,
    dirty: false,
    saving: false,
    saveAgain: false,
    saveTimer: null,
    tile: 40,
    view: null,         // what's drawn: the map plus a ring of + cells around it
    drag: null,
    hover: null,
  };

  // ---- layout ----------------------------------------------------------------------

  const title = h("h1", {}, ed.model.name);
  const statusText = h("span", { class: "save-status" });
  const playLink = h("a", { class: "button primary", href: `#/new?map=${mapId}` }, "Play this map");
  const canvas = h("canvas", { class: "editor-canvas" });
  const tip = h("div", { class: "tooltip", hidden: true });
  const undoButton = h("button", { class: "small", title: "Ctrl+Z", onclick: undo }, "Undo");
  const redoButton = h("button", { class: "small", title: "Ctrl+Y", onclick: redo }, "Redo");
  const inspector = h("div", { class: "inspector" });
  const settings = h("section", { class: "card" });
  const criteriaCard = h("section", { class: "card" });
  const problemsCard = h("section", { class: "card" });

  root.append(
    h("div", { class: "page-head" },
      h("div", {}, title, h("p", { class: "hint" }, "Changes save automatically. ", statusText)),
      h("div", { class: "head-actions" }, playLink, h("a", { class: "button", href: "#/maps" }, "All maps"))),
    h("div", { class: "layout editor-layout" },
      h("section", { class: "card board" },
        h("div", { class: "controls" },
          undoButton, redoButton,
          h("button", { class: "small", onclick: addRing, title: "Add a tile on every + cell" }, "Grow all round"),
          h("button", { class: "small", onclick: fillRectangle, title: "Fill every hole and corner inside the map's edges" }, "Fill to rectangle"),
          h("button", { class: "small", onclick: selectAll }, "Select all"),
          h("span", { class: "hint status" },
            "Click + to add a tile, or drag across + cells to add several. ",
            "Click or drag over tiles to select them; Shift adds to the selection.")),
        h("div", { class: "canvas-wrap" }, canvas, tip),
        inspector),
      h("aside", { class: "side" }, settings, criteriaCard, problemsCard)));

  // ---- changes, undo and saving ------------------------------------------------------

  const snapshot = () => JSON.stringify(toJson(ed.model));

  // Make a change. With coalesce, changes with the same label in quick succession (dragging a
  // slider, typing a name) undo as one. refresh says what to redraw: "all", or "board" while a
  // control is still in use.
  function change(label, fn, { refresh = "all", coalesce = false } = {}) {
    const now = performance.now();
    if (!coalesce || label !== ed.lastLabel || now - ed.lastAt > 800) {
      ed.history.push(snapshot());
      if (ed.history.length > 200) ed.history.shift();
    }
    ed.future = [];
    ed.lastLabel = label;
    ed.lastAt = now;
    fn();
    const [dx, dy] = normalise(ed.model);
    if (dx || dy) {
      ed.selection = new Set([...ed.selection].map((k) => { const [x, y] = unkey(k); return key(x - dx, y - dy); }));
    }
    scheduleSave();
    if (refresh === "all") render();
    else drawMap();
  }

  function restore(text) {
    ed.model = fromJson(JSON.parse(text));
    ed.selection = new Set([...ed.selection].filter((k) => ed.model.tiles.has(k)));
    ed.lastLabel = null;
    scheduleSave();
    render();
  }

  function undo() {
    if (!ed.history.length) return;
    ed.future.push(snapshot());
    restore(ed.history.pop());
  }

  function redo() {
    if (!ed.future.length) return;
    ed.history.push(snapshot());
    restore(ed.future.pop());
  }

  function setStatus(text, bad = false) {
    statusText.textContent = text;
    statusText.classList.toggle("error-text", bad);
  }

  function scheduleSave() {
    ed.dirty = true;
    setStatus("Unsaved changes");
    clearTimeout(ed.saveTimer);
    ed.saveTimer = setTimeout(save, 600);
  }

  async function save() {
    clearTimeout(ed.saveTimer);
    if (ed.saving) {
      ed.saveAgain = true;
      return;
    }
    if (!ed.dirty) return;
    ed.saving = true;
    ed.dirty = false;
    setStatus("Saving…");
    try {
      const result = await put(`/api/catalogue/maps/${mapId}`, toJson(ed.model));
      ed.problems = result.problems ?? [];
      setStatus(ed.dirty ? "Unsaved changes" : "Saved");
      renderProblems();
    } catch (e) {
      ed.dirty = true;
      setStatus(`Not saved: ${e.message}`, true);
    } finally {
      ed.saving = false;
      if (ed.saveAgain) {
        ed.saveAgain = false;
        save();
      }
    }
  }

  // ---- drawing -----------------------------------------------------------------------

  const isTile = (x, y) => ed.model.tiles.has(key(x, y));
  const isGhost = (x, y) => !isTile(x, y) && NEIGHBOURS.some(([dx, dy]) => isTile(x + dx, y + dy));

  // The map with a one-cell ring around it for the + cells. View cell (x + 1, y + 1) is map tile (x, y).
  function buildView() {
    const { width, height } = bounds(ed.model);
    const w = width + 2, ht = height + 2;
    const grid = (attr) => Array.from({ length: ht }, (_, vy) =>
      Array.from({ length: w }, (_, vx) => ed.model.tiles.get(key(vx - 1, vy - 1))?.[attr] ?? null));
    const shifted = (m, field) => [...m].map(([k, v]) => { const [x, y] = unkey(k); return { x: x + 1, y: y + 1, [field]: v }; });
    return { width: w, height: ht, dirt: grid("dirt"), food: grid("food"), plants: shifted(ed.model.plants, "rate"), starts: shifted(ed.model.starts, "slot") };
  }

  function dragCells() {
    if (!ed.drag) return [];
    const { start, end } = ed.drag;
    const cells = [];
    for (let x = Math.min(start.x, end.x); x <= Math.max(start.x, end.x); x++) {
      for (let y = Math.min(start.y, end.y); y <= Math.max(start.y, end.y); y++) cells.push({ x, y });
    }
    return cells;
  }

  function drawMap() {
    ed.view = buildView();
    const available = canvas.parentElement.clientWidth || 600;
    ed.tile = drawBoard(canvas, ed.view, { maxWidth: available, minTile: 18, maxTile: 56 });
    const size = ed.tile;
    const ctx = canvas.getContext("2d");
    const px = (x) => (x + 1) * size;
    const py = (y) => (ed.view.height - 1 - (y + 1)) * size;
    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
    const muted = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();

    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let vy = 0; vy < ed.view.height; vy++) {
      for (let vx = 0; vx < ed.view.width; vx++) {
        const x = vx - 1, y = vy - 1;
        if (isGhost(x, y)) {
          ctx.setLineDash([4, 3]);
          ctx.strokeStyle = muted;
          ctx.lineWidth = 1;
          ctx.strokeRect(px(x) + 3.5, py(y) + 3.5, size - 7, size - 7);
          ctx.setLineDash([]);
          ctx.fillStyle = muted;
          ctx.font = `${Math.round(size * 0.45)}px system-ui, sans-serif`;
          ctx.fillText("+", px(x) + size / 2, py(y) + size / 2 + 1);
        } else if (isTile(x, y) && size >= 24 && !ed.model.starts.has(key(x, y))) {
          // The height, in the corner (but not under a start's marker).
          const dirt = ed.model.tiles.get(key(x, y)).dirt;
          ctx.fillStyle = dirt > 7 ? "rgba(255,255,255,0.85)" : "rgba(0,0,0,0.45)";
          ctx.font = `600 ${Math.round(size * 0.24)}px system-ui, sans-serif`;
          ctx.fillText(String(dirt), px(x) + size * 0.2, py(y) + size * 0.8);
        }
      }
    }

    if (ed.drag && ed.drag.mode !== "none") {
      ctx.globalAlpha = 0.2;
      ctx.fillStyle = accent;
      for (const c of dragCells()) ctx.fillRect(px(c.x), py(c.y), size, size);
      ctx.globalAlpha = 1;
    }
    ctx.strokeStyle = accent;
    ctx.lineWidth = 2.5;
    for (const k of ed.selection) {
      const [x, y] = unkey(k);
      ctx.strokeRect(px(x) + 1.5, py(y) + 1.5, size - 3, size - 3);
    }
    if (ed.hover && (isTile(ed.hover.x, ed.hover.y) || isGhost(ed.hover.x, ed.hover.y))) {
      ctx.strokeStyle = muted;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(px(ed.hover.x) + 0.75, py(ed.hover.y) + 0.75, size - 1.5, size - 1.5);
    }
    undoButton.disabled = !ed.history.length;
    redoButton.disabled = !ed.future.length;
  }

  // The map tile (x, y) under the pointer, which may be a + cell or empty, or null off the canvas.
  function cellAt(event) {
    const rect = canvas.getBoundingClientRect();
    const vx = Math.floor((event.clientX - rect.left) / ed.tile);
    const vy = ed.view.height - 1 - Math.floor((event.clientY - rect.top) / ed.tile);
    if (vx < 0 || vy < 0 || vx >= ed.view.width || vy >= ed.view.height) return null;
    return { x: vx - 1, y: vy - 1 };
  }

  // ---- pointer -----------------------------------------------------------------------

  canvas.addEventListener("pointerdown", (event) => {
    const cell = cellAt(event);
    if (!cell) return;
    canvas.setPointerCapture(event.pointerId);
    ed.drag = {
      start: cell, end: cell,
      mode: isTile(cell.x, cell.y) ? "select" : isGhost(cell.x, cell.y) ? "add" : "none",
      additive: event.shiftKey || event.ctrlKey || event.metaKey,
    };
    drawMap();
  });

  canvas.addEventListener("pointermove", (event) => {
    const cell = cellAt(event);
    ed.hover = cell;
    if (ed.drag && cell) ed.drag.end = cell;
    showTip(event, cell);
    drawMap();
  });

  canvas.addEventListener("pointerleave", () => {
    ed.hover = null;
    tip.hidden = true;
    if (!ed.drag) drawMap();
  });

  canvas.addEventListener("pointerup", () => {
    const drag = ed.drag;
    if (!drag) return;
    const cells = dragCells();
    ed.drag = null;
    if (drag.mode === "add") {
      const added = cells.filter((c) => !isTile(c.x, c.y));
      change("add", () => {
        addTiles(added);
        ed.selection = new Set(added.map((c) => key(c.x, c.y)));
      });
      return;
    }
    if (drag.mode === "select") {
      const keys = cells.filter((c) => isTile(c.x, c.y)).map((c) => key(c.x, c.y));
      if (drag.additive && keys.length === 1 && ed.selection.has(keys[0])) ed.selection.delete(keys[0]);
      else if (drag.additive) keys.forEach((k) => ed.selection.add(k));
      else ed.selection = new Set(keys);
    } else if (!drag.additive) {
      ed.selection.clear();
    }
    render();
  });

  function showTip(event, cell) {
    if (!cell || ed.drag) {
      tip.hidden = true;
      return;
    }
    let text;
    if (isTile(cell.x, cell.y)) {
      const k = key(cell.x, cell.y);
      const t = ed.model.tiles.get(k);
      text = [`x=${cell.x} y=${cell.y} · height ${t.dirt} · food ${t.food}`,
        ed.model.plants.has(k) ? `plant · grows ${ed.model.plants.get(k)}/turn` : null,
        ed.model.starts.has(k) ? `start for slot ${ed.model.starts.get(k)}` : null].filter(Boolean).join("\n");
    } else if (isGhost(cell.x, cell.y)) {
      text = "Click to add a tile here";
    } else {
      tip.hidden = true;
      return;
    }
    tip.textContent = text;
    const wrap = canvas.parentElement.getBoundingClientRect();
    tip.style.left = `${event.clientX - wrap.left + 14}px`;
    tip.style.top = `${event.clientY - wrap.top + 14}px`;
    tip.hidden = false;
  }

  // ---- whole-map actions -------------------------------------------------------------

  // A new tile starts at the height of a neighbour, so plateaus are easy to extend.
  function addTiles(cells) {
    for (const c of cells) {
      const neighbour = NEIGHBOURS.map(([dx, dy]) => ed.model.tiles.get(key(c.x + dx, c.y + dy))).find(Boolean);
      ed.model.tiles.set(key(c.x, c.y), { dirt: neighbour?.dirt ?? 0, food: 0 });
    }
  }

  function addRing() {
    const ghosts = [];
    for (let vy = 0; vy < ed.view.height; vy++) {
      for (let vx = 0; vx < ed.view.width; vx++) {
        if (isGhost(vx - 1, vy - 1)) ghosts.push({ x: vx - 1, y: vy - 1 });
      }
    }
    change("ring", () => addTiles(ghosts));
  }

  function fillRectangle() {
    const { width, height } = bounds(ed.model);
    const holes = [];
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (!isTile(x, y)) holes.push({ x, y });
      }
    }
    if (holes.length) change("fill", () => addTiles(holes));
  }

  function selectAll() {
    ed.selection = new Set(ed.model.tiles.keys());
    render();
  }

  // ---- the toolbar under the map ---------------------------------------------------------

  const selectedTiles = () => [...ed.selection].map((k) => [k, ed.model.tiles.get(k)]).filter(([, t]) => t);

  function sameValue(values) {
    return values.every((v) => v === values[0]) ? values[0] : null;
  }

  function slider(label, attr, max) {
    const tiles = selectedTiles();
    const value = sameValue(tiles.map(([, t]) => t[attr]));
    const shown = h("output", { class: "value" }, value ?? "mixed");
    const set = (v) => change(attr, () => { for (const [, t] of selectedTiles()) t[attr] = v; },
      { refresh: "board", coalesce: true });
    const step = (d) => change(attr, () => { for (const [, t] of selectedTiles()) t[attr] = clamp(t[attr] + d, 0, max); },
      { coalesce: true });
    return h("div", { class: "tool" },
      h("span", { class: "tool-label" }, label),
      h("button", { class: "small", title: `Lower by 1${attr === "dirt" ? " (−)" : ""}`, onclick: () => step(-1) }, "−"),
      h("input", {
        type: "range", min: "0", max: String(max), value: String(value ?? tiles[0][1][attr]),
        oninput: (e) => { set(Number(e.target.value)); shown.textContent = e.target.value; },
        onchange: () => render(),
      }),
      h("button", { class: "small", title: `Raise by 1${attr === "dirt" ? " (+)" : ""}`, onclick: () => step(1) }, "+"),
      shown);
  }

  function renderInspector() {
    const tiles = selectedTiles();
    if (!tiles.length) {
      fill(inspector, h("p", { class: "hint" }, "Select tiles to change their height, food, plants and start slots."));
      return;
    }
    const keys = tiles.map(([k]) => k);
    const heading = tiles.length === 1
      ? `Tile ${keys[0].replace(",", ", ")}`
      : `${tiles.length} tiles`;

    // Plants.
    const planted = keys.filter((k) => ed.model.plants.has(k));
    const plantBox = h("input", {
      type: "checkbox", checked: planted.length === keys.length,
      onchange: (e) => change("plant", () => {
        for (const k of keys) {
          if (e.target.checked && !ed.model.plants.has(k)) ed.model.plants.set(k, DEFAULT_RATE);
          if (!e.target.checked) ed.model.plants.delete(k);
        }
      }),
    });
    plantBox.indeterminate = planted.length > 0 && planted.length < keys.length;
    const rate = sameValue(planted.map((k) => ed.model.plants.get(k)));

    // Start slots: the ones in use, plus the next free number.
    const slots = slotsOf(ed.model);
    const nextSlot = (slots.at(-1) ?? 0) + 1;
    const current = sameValue(keys.map((k) => ed.model.starts.get(k) ?? 0));

    // One line per section: the selection and its buttons, then food, height, plant and start.
    fill(inspector,
      h("div", { class: "tool heading" }, h("strong", {}, heading),
        h("button", { class: "small danger", title: "Delete", onclick: removeSelected },
          tiles.length === 1 ? "Remove tile" : "Remove tiles"),
        h("button", { class: "small", title: "Esc", onclick: () => { ed.selection.clear(); render(); } }, "Done")),
      slider("Food", "food", MAX_FOOD),
      slider("Height", "dirt", MAX_DIRT),
      h("div", { class: "tool" },
        h("label", { class: "tool-label" }, plantBox, " Plant"),
        planted.length ? h("label", { class: "inline" }, "grows ", h("input", {
          type: "number", min: "0", class: "short", value: rate === null ? "" : String(rate), placeholder: "mixed",
          onchange: (e) => change("rate", () => {
            const value = Math.max(0, Math.round(Number(e.target.value) || 0));
            for (const k of planted) ed.model.plants.set(k, value);
          }),
        }), "/turn") : null),
      h("div", { class: "tool" },
        h("label", { class: "tool-label" }, "Start"),
        h("select", {
          value: current === null ? "mixed" : String(current),
          onchange: (e) => change("start", () => {
            const slot = Number(e.target.value);
            for (const k of keys) {
              if (slot) ed.model.starts.set(k, slot);
              else ed.model.starts.delete(k);
            }
          }),
        },
        current === null ? h("option", { value: "mixed", disabled: true }, "mixed") : null,
        h("option", { value: "0" }, "no start"),
        slots.map((s) => h("option", { value: String(s) }, `slot ${s}`)),
        h("option", { value: String(nextSlot) }, `new slot ${nextSlot}`)),
        current ? h("span", { class: "dot", style: `background:${slotColour(current)}` }) : null));
  }

  function removeSelected() {
    const keys = selectedTiles().map(([k]) => k);
    if (!keys.length) return;
    if (keys.length >= ed.model.tiles.size) {
      showError("A map needs at least one tile, so the last one can't be removed.");
      return;
    }
    change("remove", () => {
      for (const k of keys) {
        ed.model.tiles.delete(k);
        ed.model.plants.delete(k);
        ed.model.starts.delete(k);
      }
      ed.selection.clear();
    });
  }

  // ---- the side panel ------------------------------------------------------------------

  function renderSettings() {
    const m = ed.model;
    const { width, height } = bounds(m);
    const name = h("input", {
      value: m.name, class: "grow",
      oninput: (e) => {
        const value = e.target.value.trim();
        if (!value) return;  // keep the old name until there's a new one
        change("name", () => { m.name = value; }, { refresh: "board", coalesce: true });
        title.textContent = value;
      },
    });
    fill(settings,
      h("div", { class: "card-head" }, h("h2", {}, "Map")),
      h("div", { class: "fields" },
        h("label", {}, "Name", name),
        h("label", {}, "Speed", h("select", {
          value: m.mode,
          onchange: (e) => change("mode", () => { m.mode = e.target.value; }),
        }, Object.entries(MODES).map(([mode, text]) => h("option", { value: mode }, `${mode} · ${text}`)))),
        h("label", {}, "Max agents per team", h("input", {
          type: "number", min: "1", value: String(m.maxAgents),
          onchange: (e) => change("maxAgents", () => { m.maxAgents = Math.max(1, Math.round(Number(e.target.value) || 1)); }),
        }))),
      h("p", { class: "hint" },
        `${width}×${height} · ${m.tiles.size} tile${m.tiles.size === 1 ? "" : "s"} · `,
        `${m.plants.size} plant${m.plants.size === 1 ? "" : "s"} · `,
        `${slotsOf(m).length} start slot${slotsOf(m).length === 1 ? "" : "s"}`));
    return name;
  }

  function criterionRow(c, index) {
    const m = ed.model;
    const spec = ref.criteria[c.type] ?? [];
    const update = (field, value) => change("criteria", () => { m.criteria[index][field] = value; });
    const fields = spec.map(([field, kind]) => {
      if (kind === "slot") {
        const slots = [...new Set([...slotsOf(m), c.slot])].sort((a, b) => a - b);
        return h("select", { value: String(c.slot), onchange: (e) => update(field, Number(e.target.value)) },
          slots.map((s) => h("option", { value: String(s) }, `slot ${s}`)));
      }
      if (kind === "action") {
        return h("select", { value: c.action, onchange: (e) => update(field, e.target.value) },
          ref.actions.filter((a) => !["CONFUSED", "DEATH"].includes(a.name)).map((a) => h("option", { value: a.name }, a.name)));
      }
      if (kind === "thing") {
        const plants = [...m.plants.keys()].map((k, n) => [`Plant${n}`, k.replace(",", ", ")]);
        return h("select", { value: c.thing, onchange: (e) => update(field, e.target.value) },
          plants.length ? plants.map(([id, at]) => h("option", { value: id }, `${id} at ${at}`))
            : h("option", { value: c.thing }, `${c.thing} (no plants yet)`));
      }
      return h("label", { class: "inline" }, field, h("input", {
        type: "number", min: "0", class: "short", value: String(c[field]),
        onchange: (e) => update(field, Math.max(0, Math.round(Number(e.target.value) || 0))),
      }));
    });
    const single = selectedTiles().length === 1 ? unkey(selectedTiles()[0][0]) : null;
    const hasXY = spec.some(([, kind]) => kind === "x");
    return h("li", { class: "criterion" },
      h("div", { class: "criterion-head" },
        h("span", {}, describeCriterion(c, (s) => `Slot ${s}`)),
        h("button", {
          class: "small danger", title: "Remove",
          onclick: () => change("criteria", () => { m.criteria.splice(index, 1); }),
        }, "×")),
      h("div", { class: "criterion-fields" }, h("code", {}, c.type), fields,
        hasXY ? h("button", {
          class: "small", disabled: !single, title: single ? "" : "Select one tile first",
          onclick: () => change("criteria", () => { [m.criteria[index].x, m.criteria[index].y] = single; }),
        }, "Use selected tile") : null));
  }

  function renderCriteria() {
    const m = ed.model;
    const add = h("select", {
      onchange: (e) => {
        const type = e.target.value;
        if (!type) return;
        const criterion = { type };
        for (const [field, kind] of ref.criteria[type]) {
          criterion[field] = kind === "slot" ? (slotsOf(m)[0] ?? 1)
            : kind === "thing" ? "Plant0" : CRITERION_DEFAULTS[field] ?? 0;
        }
        change("criteria", () => { m.criteria.push(criterion); });
      },
    }, h("option", { value: "" }, "Add a win condition…"),
    Object.keys(ref.criteria).map((type) => h("option", { value: type }, type)));
    fill(criteriaCard,
      h("div", { class: "card-head" }, h("h2", {}, "Win conditions"),
        h("span", { class: "hint" }, "The game ends when any is met")),
      m.criteria.length
        ? h("ul", { class: "plain criteria-list" }, m.criteria.map(criterionRow))
        : h("p", { class: "empty" }, "None, so a game runs until no agents are left."),
      add);
  }

  function renderProblems() {
    const ready = !ed.problems.length;
    playLink.classList.toggle("disabled", !ready);
    playLink.title = ready ? "" : "Fix the problems listed first";
    fill(problemsCard,
      h("div", { class: "card-head" }, h("h2", {}, "Ready to play?")),
      ready
        ? h("p", {}, h("span", { class: "badge ok" }, "ready"), " This map can be played.")
        : h("ul", { class: "plain problems" }, ed.problems.map((p) => h("li", {}, p))));
  }

  function render() {
    drawMap();
    renderInspector();
    renderSettings();
    renderCriteria();
    renderProblems();
  }

  // ---- keys and leaving ------------------------------------------------------------------

  const onKey = (event) => {
    const typing = event.target.closest("input, textarea, select");
    const mod = event.ctrlKey || event.metaKey;
    if (mod && event.key.toLowerCase() === "z" && !typing) {
      event.preventDefault();
      event.shiftKey ? redo() : undo();
    } else if (mod && event.key.toLowerCase() === "y" && !typing) {
      event.preventDefault();
      redo();
    } else if (typing) {
      return;
    } else if (event.key === "Escape") {
      ed.selection.clear();
      render();
    } else if ((event.key === "Delete" || event.key === "Backspace") && ed.selection.size) {
      event.preventDefault();
      removeSelected();
    } else if ((event.key === "+" || event.key === "=") && ed.selection.size) {
      change("dirt", () => { for (const [, t] of selectedTiles()) t.dirt = clamp(t.dirt + 1, 0, MAX_DIRT); }, { coalesce: true });
    } else if (event.key === "-" && ed.selection.size) {
      change("dirt", () => { for (const [, t] of selectedTiles()) t.dirt = clamp(t.dirt - 1, 0, MAX_DIRT); }, { coalesce: true });
    }
  };
  const onUnload = (event) => {
    if (ed.dirty || ed.saving) event.preventDefault();
  };
  const onResize = () => drawMap();
  document.addEventListener("keydown", onKey);
  window.addEventListener("beforeunload", onUnload);
  window.addEventListener("resize", onResize);

  render();
  setStatus("Saved");
  if (query.get("new")) {
    // A brand new map: start with its one tile selected and the name ready to type over.
    ed.selection = new Set(ed.model.tiles.keys());
    const name = renderSettings();
    renderInspector();
    drawMap();
    name.focus();
    name.select();
  }

  return () => {
    document.removeEventListener("keydown", onKey);
    window.removeEventListener("beforeunload", onUnload);
    window.removeEventListener("resize", onResize);
    if (ed.dirty) save().catch(() => showError("The last map change wasn't saved."));
  };
}
