// Watching a game: the board, the teams, the selected agent, its tree and the event log.
// #/play/<game id>?turn=40 opens the game and runs it to turn 40.

import { get, post } from "../api.js";
import { drawBoard, tileAt } from "../board.js";
import { teamColour } from "../colours.js";
import { h, showError } from "../dom.js";
import { newUi, treeView } from "../treeview.js";

const DEFAULT_SPEED = { CLICK: "2", FIXED: "1", CONST: "25" };
const MAX_EVENTS = 400;

const TEMPLATE = `
  <div class="page-head">
    <div><h1 data-id="game-name">Game</h1><p class="hint" data-id="game-meta"></p></div>
    <div class="head-actions">
      <a class="button" href="#/new">New game</a>
      <a class="button" href="#/games">Load game</a>
    </div>
  </div>
  <div class="layout">
    <section class="card board">
      <div class="controls">
        <button data-id="play" class="primary" title="Space">Play</button>
        <button data-id="back10" title="Back 10 turns">−10</button>
        <button data-id="back" title="Back a turn (left arrow)">Back</button>
        <button data-id="step" title="Right arrow">Step</button>
        <button data-id="step10">+10</button>
        <label class="speed">Speed
          <select data-id="speed">
            <option value="1">1 turn/s</option>
            <option value="2">2 turns/s</option>
            <option value="5">5 turns/s</option>
            <option value="10">10 turns/s</option>
            <option value="25">25 turns/s</option>
            <option value="100">100 turns/s</option>
          </select>
        </label>
        <button data-id="reset">Reset</button>
        <span data-id="status" class="status"></span>
      </div>
      <div data-id="outcome" class="banner outcome" hidden></div>
      <div class="canvas-wrap">
        <canvas data-id="board"></canvas>
        <div data-id="tooltip" class="tooltip" hidden></div>
      </div>
      <div class="legend">
        <span><i class="swatch dirt-low"></i><i class="swatch dirt-high"></i> height</span>
        <span><i class="swatch food"></i> food</span>
        <span><i class="swatch plant"></i> plant</span>
        <span>ring = health</span>
        <span>y = 0 is the bottom row, so UP moves up</span>
      </div>
    </section>
    <aside class="side">
      <section class="card">
        <div class="card-head"><h2>Teams</h2><span data-id="criteria" class="hint"></span></div>
        <div data-id="teams"></div>
      </section>
      <section class="card">
        <div class="card-head"><h2>Agent</h2><span class="hint">Click an agent to inspect it</span></div>
        <div data-id="agent"></div>
      </section>
      <section class="card">
        <div class="card-head"><h2>Decision tree</h2><div data-id="tree-tabs" class="tabs"></div></div>
        <div data-id="tree"></div>
      </section>
      <section class="card">
        <div class="card-head">
          <h2>Events</h2>
          <label class="hint"><input type="checkbox" data-id="show-fails"> failed actions</label>
        </div>
        <ol data-id="events" class="events" reversed></ol>
      </section>
    </aside>
  </div>`;

export async function mount(root, [gameId], query) {
  root.innerHTML = TEMPLATE;
  const $ = (id) => root.querySelector(`[data-id="${id}"]`);

  const app = {
    game: null,         // last response from the server
    state: null,        // app.game.state, the world
    events: [],         // recent events, oldest first
    selected: null,     // selected agent id
    treeTab: null,      // tree name chosen in the tabs, or null for the agent's current tree
    treeUi: new Map(),  // "team/tree" -> the outline's open/closed state
    playing: false,
    busy: false,
    timer: null,
    tile: 32,           // tile size in CSS pixels
  };

  const colourOf = (name) => teamColour(app.state.players, name);
  const selectedAgent = () => app.state?.agents.find((a) => a.id === app.selected) ?? null;

  // ---- game lifecycle --------------------------------------------------------------

  function applyResponse(data, replaceEvents = false) {
    app.game = data;
    app.state = data.state;
    app.events = replaceEvents ? data.events.slice() : app.events.concat(data.events);
    if (app.events.length > MAX_EVENTS) app.events = app.events.slice(-MAX_EVENTS);
    if (app.selected === null && app.state.agents.length) app.selected = app.state.agents[0].id;
    showError("");
    render();
  }

  async function step(turns) {
    if (!app.game || app.busy || app.state.finished) return;
    app.busy = true;
    try {
      applyResponse(await post(`/api/games/${app.game.id}/step`, { turns }));
    } catch (e) {
      pause();
      showError(e.message);
    } finally {
      app.busy = false;
    }
  }

  // Going back replays the game from its seed on the server, so it's exact.
  async function seek(turn) {
    if (!app.game || app.busy) return;
    pause();
    app.busy = true;
    try {
      applyResponse(await post(`/api/games/${app.game.id}/seek`, { turn: Math.max(0, turn) }), true);
    } catch (e) {
      showError(e.message);
    } finally {
      app.busy = false;
    }
  }

  async function reset() {
    pause();
    try {
      app.events = [];
      applyResponse(await post(`/api/games/${app.game.id}/reset`), true);
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

  // ---- rendering -------------------------------------------------------------------

  function render() {
    const s = app.state;
    $("game-name").textContent = app.game.name;
    $("game-meta").textContent = `seed ${s.seed} · ${s.mode} · ${s.width}×${s.height}`;
    $("status").textContent = `Turn ${s.time}`;
    $("outcome").hidden = !s.finished;
    $("outcome").textContent = s.outcome ?? "";
    $("step").disabled = $("step10").disabled = $("play").disabled = s.finished;
    $("back").disabled = $("back10").disabled = s.time === 0;
    drawGame();
    renderTeams();
    renderAgent();
    renderTree();
    renderEvents();
  }

  function drawGame() {
    app.tile = drawBoard($("board"), app.state, {
      selected: app.selected,
      colourOf: (agent) => colourOf(agent.player),
    });
  }

  function renderTeams() {
    const s = app.state;
    $("criteria").textContent = s.criteria.length ? `Win: ${s.criteria.join(" · ")}` : "";
    $("teams").replaceChildren(...s.players.map((player) =>
      h("div", { class: "team" },
        h("div", { class: "team-row" },
          h("span", { class: "dot", style: `background:${colourOf(player.name)}` }),
          h("span", { class: "team-name" }, player.name),
          h("span", { class: "team-count" },
            `${player.alive} alive · ${player.total} ever · max ${player.maxAgents}`)),
        h("div", { class: "chips" },
          s.agents.filter((a) => a.player === player.name).map((agent) =>
            h("button", {
              class: `chip${agent.id === app.selected ? " selected" : ""}`,
              onclick: () => select(agent.id),
            }, agent.id))))));
  }

  function renderAgent() {
    const box = $("agent");
    const agent = selectedAgent();
    if (!agent) {
      box.replaceChildren(h("p", { class: "empty" },
        app.selected ? `${app.selected} isn't alive at turn ${app.state.time}.` : "No agent selected."));
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
    box.replaceChildren(h("dl", { class: "stats" }, rows.map(([label, value]) => [
      h("dt", {}, label),
      h("dd", {}, value, label === "Health"
        ? h("div", { class: "bar" },
          h("i", { style: `width:${Math.max(0, (agent.health / agent.maxHealth) * 100)}%` }))
        : null),
    ])));
  }

  function renderTree() {
    const box = $("tree");
    const tabs = $("tree-tabs");
    const agent = selectedAgent();
    if (!agent) {
      tabs.replaceChildren();
      box.replaceChildren(h("p", { class: "empty" }, "Select an agent to see its tree."));
      return;
    }
    const player = app.state.players.find((p) => p.name === agent.player);
    const shownName = app.treeTab ?? agent.tree;
    tabs.replaceChildren(...player.trees.map((tree) =>
      h("button", {
        class: `tab${tree.name === shownName ? " current" : ""}`,
        title: tree.name === agent.tree ? "This agent's current tree" : "Another tree on this team",
        onclick: () => { app.treeTab = tree.name; renderTree(); },
      }, tree.name)));
    const tree = player.trees.find((t) => t.name === shownName) ?? player.trees[0];
    const key = `${player.name}/${tree.name}`;
    if (!app.treeUi.has(key)) app.treeUi.set(key, newUi());
    // Only highlight the path on the tree the agent actually used for its last decision.
    const path = new Set(tree.name === agent.pathTree ? agent.path : []);
    const scroll = box.querySelector(".tree")?.scrollTop ?? 0;
    box.replaceChildren(treeView(tree.root, app.treeUi.get(key), {
      path,
      defaultOpen: (node, depth, onPath) => onPath || depth < 1,
      onChange: renderTree,
    }));
    box.querySelector(".tree").scrollTop = scroll;
  }

  function renderEvents() {
    const showFails = $("show-fails").checked;
    const list = $("events");
    const shown = app.events.filter((e) => showFails || e.kind !== "fail").slice(-150).reverse();
    if (!shown.length) {
      list.replaceChildren(h("li", { class: "empty" }, "Nothing yet."));
      return;
    }
    list.replaceChildren(...shown.map((event) =>
      h("li", {
        class: event.kind,
        style: event.agent ? "cursor:pointer" : null,
        onclick: event.agent ? () => select(event.agent) : null,
      }, h("span", { class: "t" }, event.time), h("span", {}, event.message))));
  }

  function select(agentId) {
    app.selected = agentId;
    app.treeTab = null;
    render();
  }

  function showTooltip(event) {
    const tip = $("tooltip");
    const tile = tileAt($("board"), app.state, app.tile, event);
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

  // ---- wiring ----------------------------------------------------------------------

  const data = await get(`/api/games/${gameId}`);
  $("speed").value = DEFAULT_SPEED[data.state.mode] ?? "2";
  applyResponse(data, true);

  $("play").addEventListener("click", () => (app.playing ? pause() : play()));
  $("step").addEventListener("click", () => step(1));
  $("step10").addEventListener("click", () => step(10));
  $("back").addEventListener("click", () => seek(app.state.time - 1));
  $("back10").addEventListener("click", () => seek(app.state.time - 10));
  $("reset").addEventListener("click", reset);
  $("show-fails").addEventListener("change", renderEvents);
  const board = $("board");
  board.addEventListener("click", (event) => {
    const tile = tileAt(board, app.state, app.tile, event);
    const agent = tile && app.state.agents.find((a) => a.x === tile.x && a.y === tile.y);
    if (agent) select(agent.id);
  });
  board.addEventListener("mousemove", showTooltip);
  board.addEventListener("mouseleave", () => { $("tooltip").hidden = true; });

  const onKey = (event) => {
    if (event.target.closest("input, textarea, select")) return;
    if (event.key === " ") {
      event.preventDefault();
      app.playing ? pause() : play();
    } else if (event.key === "ArrowRight") {
      step(1);
    } else if (event.key === "ArrowLeft") {
      seek(app.state.time - 1);
    }
  };
  const onResize = () => drawGame();
  document.addEventListener("keydown", onKey);
  window.addEventListener("resize", onResize);

  const turn = Math.min(1000, Number(query.get("turn")) || 0);
  if (turn > 0) await step(turn);

  return () => {
    pause();
    document.removeEventListener("keydown", onKey);
    window.removeEventListener("resize", onResize);
  };
}
