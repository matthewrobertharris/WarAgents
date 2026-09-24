"use strict";

const $ = (id) => document.getElementById(id);

// Teams named after a colour get that colour; others take the next palette entry.
const NAMED_COLOURS = {
  red: "#e03131", green: "#2f9e44", blue: "#1c7ed6", yellow: "#f08c00",
  orange: "#e8590c", purple: "#9c36b5", pink: "#d6336c", teal: "#0ca678",
};
const PALETTE = ["#1c7ed6", "#e8590c", "#9c36b5", "#0ca678", "#f08c00", "#d6336c", "#495057"];
const DEFAULT_SPEED = { CLICK: "2", FIXED: "1", CONST: "25" };
const MAX_EVENTS = 400;

const app = {
  game: null,         // last response from the server
  state: null,        // app.game.state, the world
  events: [],         // recent events, oldest first
  selected: null,     // selected agent id
  treeTab: null,      // tree name chosen in the tabs, or null for the agent's current tree
  playing: false,
  busy: false,
  timer: null,
  tile: 32,           // tile size in CSS pixels
  editorDirty: false,
};

// ---- helpers -----------------------------------------------------------------

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join("; ") : data.detail;
    throw new Error(detail || res.statusText);
  }
  return data;
}

function showError(message) {
  const banner = $("error");
  banner.textContent = message;
  banner.hidden = !message;
}

function teamColour(name) {
  if (NAMED_COLOURS[name.toLowerCase()]) return NAMED_COLOURS[name.toLowerCase()];
  const index = app.state.players.findIndex((p) => p.name === name);
  return PALETTE[index % PALETTE.length];
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function selectedAgent() {
  return app.state?.agents.find((a) => a.id === app.selected) ?? null;
}

// ---- game lifecycle ----------------------------------------------------------

async function newGame(source) {
  pause();
  const seedText = $("seed").value.trim();
  const body = { ...source, seed: seedText === "" ? null : Number(seedText) };
  const data = await api("/api/games", body);
  app.selected = null;
  app.treeTab = null;
  app.events = [];
  app.editorDirty = false;
  $("speed").value = DEFAULT_SPEED[data.state.mode] ?? "2";
  $("editor-error").textContent = "";
  applyResponse(data, true);
}

function applyResponse(data, replaceEvents = false) {
  app.game = data;
  app.state = data.state;
  app.events = replaceEvents ? data.events.slice() : app.events.concat(data.events);
  if (app.events.length > MAX_EVENTS) app.events = app.events.slice(-MAX_EVENTS);
  if (app.selected === null && app.state.agents.length) app.selected = app.state.agents[0].id;
  if (!app.editorDirty) $("map-text").value = data.text;
  showError("");
  render();
}

async function step(turns) {
  if (!app.game || app.busy || app.state.finished) return;
  app.busy = true;
  try {
    applyResponse(await api(`/api/games/${app.game.id}/step`, { turns }));
  } catch (e) {
    pause();
    showError(e.message);
  } finally {
    app.busy = false;
  }
}

async function reset() {
  if (!app.game) return;
  pause();
  try {
    app.events = [];
    applyResponse(await api(`/api/games/${app.game.id}/reset`, {}), true);
  } catch (e) {
    showError(e.message);
  }
}

function play() {
  if (!app.game || app.state.finished) return;
  app.playing = true;
  $("play").textContent = "Pause";
  tick();
}

function pause() {
  app.playing = false;
  clearTimeout(app.timer);
  $("play").textContent = "Play";
}

async function tick() {
  if (!app.playing) return;
  // Above 10 turns a second, ask for several turns per request rather than more requests.
  const speed = Number($("speed").value);
  const interval = Math.max(100, 1000 / speed);
  const turns = Math.max(1, Math.round((speed * interval) / 1000));
  const started = performance.now();
  await step(turns);
  if (!app.playing || app.state.finished) {
    pause();
    return;
  }
  app.timer = setTimeout(tick, Math.max(0, interval - (performance.now() - started)));
}

// ---- rendering ---------------------------------------------------------------

function render() {
  if (!app.state) return;
  const s = app.state;
  $("status").textContent = `Turn ${s.time} · ${s.mode} · seed ${s.seed}`;
  const outcome = $("outcome");
  outcome.hidden = !s.finished;
  outcome.textContent = s.outcome ?? "";
  $("step").disabled = $("step10").disabled = $("play").disabled = s.finished;
  drawBoard();
  renderTeams();
  renderAgent();
  renderTree();
  renderEvents();
}

function mix(a, b, t) {
  return a.map((v, i) => Math.round(v + (b[i] - v) * t));
}

function drawBoard() {
  const s = app.state;
  const canvas = $("board");
  const available = canvas.parentElement.clientWidth || 600;
  const size = Math.max(14, Math.min(48, Math.floor(available / s.width)));
  const dpr = window.devicePixelRatio || 1;
  canvas.width = s.width * size * dpr;
  canvas.height = s.height * size * dpr;
  canvas.style.width = `${s.width * size}px`;
  canvas.style.height = `${s.height * size}px`;
  app.tile = size;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const maxDirt = Math.max(4, ...s.dirt.flat());
  const low = [233, 223, 201];
  const high = [138, 98, 64];
  const py = (y) => (s.height - 1 - y) * size;  // y = 0 is the bottom row

  for (let y = 0; y < s.height; y++) {
    for (let x = 0; x < s.width; x++) {
      const [r, g, b] = mix(low, high, s.dirt[y][x] / maxDirt);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(x * size, py(y), size, size);
      const food = s.food[y][x];
      if (food > 0) {
        ctx.fillStyle = `rgba(116,184,22,${Math.min(0.7, 0.12 + food / 60)})`;
        ctx.fillRect(x * size, py(y), size, size);
      }
      ctx.strokeStyle = "rgba(0,0,0,0.07)";
      ctx.strokeRect(x * size + 0.5, py(y) + 0.5, size - 1, size - 1);
    }
  }

  for (const plant of s.plants) {
    const cx = plant.x * size + size * 0.78;
    const cy = py(plant.y) + size * 0.22;
    ctx.fillStyle = "#2b8a3e";
    ctx.beginPath();
    ctx.arc(cx, cy, size * 0.15, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#b2f2bb";
    ctx.beginPath();
    ctx.arc(cx, cy, size * 0.06, 0, Math.PI * 2);
    ctx.fill();
  }

  for (const agent of s.agents) {
    const colour = teamColour(agent.player);
    const cx = agent.x * size + size / 2;
    const cy = py(agent.y) + size / 2;
    const r = size * 0.36;
    const ring = Math.max(2, size * 0.09);
    ctx.fillStyle = colour;
    ctx.beginPath();
    ctx.arc(cx, cy, r - ring, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = ring;
    ctx.strokeStyle = "rgba(0,0,0,0.18)";
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = colour;
    ctx.beginPath();
    const health = Math.max(0, agent.health) / agent.maxHealth;
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * health);
    ctx.stroke();
    if (agent.dirt || agent.food) {
      ctx.fillStyle = agent.food ? "#d8f5a2" : "#5c3d1e";
      const d = size * 0.14;
      ctx.fillRect(cx - d / 2, cy - d / 2, d, d);
    }
    if (agent.id === app.selected) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = cssVar("--ink");
      ctx.beginPath();
      ctx.arc(cx, cy, r + ring, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

function tileAt(event) {
  const rect = $("board").getBoundingClientRect();
  const x = Math.floor((event.clientX - rect.left) / app.tile);
  const y = app.state.height - 1 - Math.floor((event.clientY - rect.top) / app.tile);
  if (x < 0 || y < 0 || x >= app.state.width || y >= app.state.height) return null;
  return { x, y };
}

function renderTeams() {
  const s = app.state;
  $("criteria").textContent = s.criteria.length ? `Win: ${s.criteria.join(" · ")}` : "";
  const box = $("teams");
  box.replaceChildren();
  for (const player of s.players) {
    const team = el("div", "team");
    const row = el("div", "team-row");
    const dot = el("span", "dot");
    dot.style.background = teamColour(player.name);
    row.append(dot, el("span", "team-name", player.name),
      el("span", "team-count", `${player.alive} alive · ${player.total} ever · max ${player.maxAgents}`));
    const chips = el("div", "chips");
    for (const agent of s.agents.filter((a) => a.player === player.name)) {
      const chip = el("button", `chip${agent.id === app.selected ? " selected" : ""}`, agent.id);
      chip.addEventListener("click", () => select(agent.id));
      chips.append(chip);
    }
    team.append(row, chips);
    box.append(team);
  }
}

function renderAgent() {
  const box = $("agent");
  box.replaceChildren();
  const agent = selectedAgent();
  if (!agent) {
    box.append(el("p", "empty", app.selected ? `${app.selected} has died.` : "No agent selected."));
    return;
  }
  const pos = (p) => (p ? `${p.x}, ${p.y}` : "not set");
  const rows = [
    ["Agent", `${agent.id} (${agent.player})`],
    ["Health", `${agent.health} / ${agent.maxHealth}`],
    ["Position", `${agent.x}, ${agent.y}`],
    ["Last action", agent.action ?? "none yet"],
    ["Tree", agent.tree],
    ["Power · speed", `${agent.power} · ${agent.speed}`],
    ["Carrying", agent.dirt ? `${agent.dirt} dirt` : agent.food ? `${agent.food} food` : "nothing"],
    ["Primary", pos(agent.primary)],
    ["Secondary", pos(agent.secondary)],
    ["Born", `turn ${agent.birth}`],
  ];
  const dl = el("dl", "stats");
  for (const [label, value] of rows) {
    const dd = el("dd", "", value);
    if (label === "Health") {
      const bar = el("div", "bar");
      const fill = el("i");
      fill.style.width = `${Math.max(0, (agent.health / agent.maxHealth) * 100)}%`;
      bar.append(fill);
      dd.append(bar);
    }
    dl.append(el("dt", "", label), dd);
  }
  box.append(dl);
}

function renderTree() {
  const box = $("tree");
  const tabs = $("tree-tabs");
  box.replaceChildren();
  tabs.replaceChildren();
  const agent = selectedAgent();
  if (!agent) {
    box.append(el("p", "empty", "Select an agent to see its tree."));
    return;
  }
  const player = app.state.players.find((p) => p.name === agent.player);
  const shownName = app.treeTab ?? agent.tree;
  for (const tree of player.trees) {
    const tab = el("button", `tab${tree.name === shownName ? " current" : ""}`, tree.name);
    tab.title = tree.name === agent.tree ? "This agent's current tree" : "Another tree on this team";
    tab.addEventListener("click", () => { app.treeTab = tree.name; renderTree(); });
    tabs.append(tab);
  }
  const tree = player.trees.find((t) => t.name === shownName) ?? player.trees[0];
  // Only highlight the path on the tree the agent actually used for its last decision.
  const path = new Set(tree.name === agent.pathTree ? agent.path : []);
  const ul = el("ul");
  ul.append(renderNode(tree.root, null, path));
  box.append(ul);
}

function renderNode(node, branch, path) {
  const li = el("li");
  const row = el("span", `node${path.has(node.id) ? " on-path" : ""}`);
  if (branch !== null) row.append(el("span", "branch", branch));
  row.append(el("span", `kind ${node.kind}`, node.kind === "OUTPUT" ? "DO" : node.kind),
    el("span", "label", node.label));
  li.append(row);
  if (node.children.length) {
    const ul = el("ul");
    node.children.forEach((child, i) => ul.append(renderNode(child, node.branches[i], path)));
    li.append(ul);
  }
  return li;
}

function renderEvents() {
  const showFails = $("show-fails").checked;
  const list = $("events");
  list.replaceChildren();
  const shown = app.events.filter((e) => showFails || e.kind !== "fail").slice(-150).reverse();
  if (!shown.length) {
    list.append(el("li", "empty", "Nothing yet."));
    return;
  }
  for (const event of shown) {
    const li = el("li", event.kind);
    li.append(el("span", "t", event.time), el("span", "", event.message));
    if (event.agent) {
      li.style.cursor = "pointer";
      li.addEventListener("click", () => select(event.agent));
    }
    list.append(li);
  }
}

function select(agentId) {
  app.selected = agentId;
  app.treeTab = null;
  render();
}

// ---- tooltip -----------------------------------------------------------------

function showTooltip(event) {
  const tip = $("tooltip");
  const tile = app.state && tileAt(event);
  if (!tile) {
    tip.hidden = true;
    return;
  }
  const s = app.state;
  const lines = [`x=${tile.x} y=${tile.y} · height ${s.dirt[tile.y][tile.x]} · food ${s.food[tile.y][tile.x]}`];
  const plant = s.plants.find((p) => p.x === tile.x && p.y === tile.y);
  if (plant) lines.push(`${plant.id} · grows ${plant.rate}/turn`);
  const agent = s.agents.find((a) => a.x === tile.x && a.y === tile.y);
  if (agent) lines.push(`${agent.id} (${agent.player}) · ${agent.health}/${agent.maxHealth} · ${agent.action ?? "no action yet"}`);
  tip.textContent = lines.join("\n");
  const wrap = $("board").parentElement.getBoundingClientRect();
  tip.style.left = `${event.clientX - wrap.left + 14}px`;
  tip.style.top = `${event.clientY - wrap.top + 14}px`;
  tip.hidden = false;
}

// ---- map list and reference ---------------------------------------------------

async function loadMaps() {
  const maps = await api("/api/maps");
  const select = $("map-select");
  const groups = { demo: "Demo maps", java: "Maps from the Java version" };
  for (const [group, label] of Object.entries(groups)) {
    const optgroup = el("optgroup");
    optgroup.label = label;
    for (const map of maps.filter((m) => m.group === group)) {
      const option = el("option", "", map.error ? `${map.name} (can't load)` : map.name);
      option.value = map.id;
      option.disabled = Boolean(map.error);
      if (map.error) option.title = map.error;
      optgroup.append(option);
    }
    if (optgroup.children.length) select.append(optgroup);
  }
  const preferred = maps.find((m) => m.id === "demo/skirmish" && !m.error) ?? maps.find((m) => !m.error);
  if (preferred) select.value = preferred.id;
}

async function loadReference() {
  const ref = await api("/api/reference");
  const box = $("reference");
  const section = (title, items) => {
    box.append(el("h3", "", title));
    const ul = el("ul");
    for (const [code, doc] of items) {
      const li = el("li");
      li.append(el("code", "", code));
      if (doc) li.append(el("span", "doc", ` ${doc}`));
      ul.append(li);
    }
    box.append(ul);
  };
  const withArgs = (x) => [x.name, ...x.args].join(" ");
  section("Nodes", [
    ["(OUTPUT action)", "a leaf: do this"],
    ["(BOOLEAN input yes no)", "2 branches"],
    ["(NUMERIC a b lt eq gt)", "compares two numeric inputs"],
    ["(POSITION input left right up down here)", "which way to the position"],
  ]);
  for (const kind of ["boolean", "numeric", "position"]) {
    section(`${kind} inputs`, ref.inputs.filter((i) => i.kind === kind).map((i) => [withArgs(i), i.doc]));
  }
  section("Positions", ref.positions.map((p) => [p, ""]));
  section("Actions", ref.actions.map((a) => [withArgs(a), ""]));
  section("Criteria", ref.criteria.map((c) => [c, ""]));
}

// ---- wiring ------------------------------------------------------------------

function wire() {
  $("new-game").addEventListener("submit", (e) => {
    e.preventDefault();
    newGame({ map: $("map-select").value }).catch((err) => showError(err.message));
  });
  $("toggle-editor").addEventListener("click", () => {
    const editor = $("editor");
    editor.hidden = !editor.hidden;
    $("toggle-editor").textContent = editor.hidden ? "Edit map" : "Hide editor";
  });
  $("map-text").addEventListener("input", () => { app.editorDirty = true; });
  $("run-text").addEventListener("click", () => {
    $("editor-error").textContent = "";
    newGame({ text: $("map-text").value }).catch((err) => { $("editor-error").textContent = err.message; });
  });
  $("play").addEventListener("click", () => (app.playing ? pause() : play()));
  $("step").addEventListener("click", () => step(1));
  $("step10").addEventListener("click", () => step(10));
  $("reset").addEventListener("click", reset);
  $("show-fails").addEventListener("change", renderEvents);

  const board = $("board");
  board.addEventListener("click", (event) => {
    const tile = tileAt(event);
    const agent = tile && app.state.agents.find((a) => a.x === tile.x && a.y === tile.y);
    if (agent) select(agent.id);
  });
  board.addEventListener("mousemove", showTooltip);
  board.addEventListener("mouseleave", () => { $("tooltip").hidden = true; });

  document.addEventListener("keydown", (event) => {
    if (event.target.closest("input, textarea, select")) return;
    if (event.key === " ") {
      event.preventDefault();
      app.playing ? pause() : play();
    } else if (event.key === "ArrowRight") {
      step(1);
    }
  });
  window.addEventListener("resize", () => app.state && drawBoard());
}

async function start() {
  wire();
  // ?map=demo/skirmish&seed=3&turn=40 opens that exact game position.
  const params = new URLSearchParams(location.search);
  try {
    await Promise.all([loadMaps(), loadReference()]);
    if (params.has("map")) $("map-select").value = params.get("map");
    if (params.has("seed")) $("seed").value = params.get("seed");
    await newGame({ map: $("map-select").value });
    const turn = Math.min(1000, Number(params.get("turn")) || 0);
    if (turn > 0) await step(turn);
  } catch (e) {
    showError(e.message);
  }
}

start();
