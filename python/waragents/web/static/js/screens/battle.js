// Battle (#/battle): set up a Skirmish. Pick a map, your tree and who to fight in each of the
// map's other start slots: other players (who play their default tree) or practice bots. The
// battle is decided on the server straight away, and you land on its result.
// ?map=<id> picks the map, and ?opponent=<player id> puts that player in the first slot.

import { get, post, reference } from "../api.js";
import { mapPreview } from "../board.js";
import { slotColour } from "../colours.js";
import { teamCost, usableTrees } from "../cost.js";
import { empty, fill, h, showError } from "../dom.js";
import { battleTabs, plural } from "../format.js";
import { user } from "../session.js";
import { describeCriterion } from "./newgame.js";

export async function mount(root, _params, query) {
  const [maps, trees, opponents, bots, ref] = await Promise.all([
    get("/api/catalogue/maps"), get("/api/catalogue/trees"), get("/api/opponents"), get("/api/bots"), reference(),
  ]);
  const me = user();
  const playable = maps.filter((m) => !m.error && !m.problems?.length && m.slots.length >= 2);
  const usable = usableTrees(trees, me.id);
  const factor = ref.progression.modeXpFactor.skirmish;

  // Each of my usable trees with its cost (with the trees it switches to) and what's stopping it.
  const choices = Object.values(usable).map((t) => {
    const cost = teamCost(t, usable, ref).cost;
    const problem = t.problems?.length ? "not finished" : cost > me.budget ? `over budget (${cost} points)` : null;
    return { tree: t, cost, problem, mine: t.owner === me.id };
  }).sort((a, b) => b.mine - a.mine || a.tree.name.localeCompare(b.tree.name));

  const state = {
    mapId: playable.find((m) => m.id === query.get("map"))?.id ?? playable[0]?.id ?? null,
    tree: (choices.find((c) => c.tree.name === me.startTree && !c.problem) ?? choices.find((c) => !c.problem))?.tree.name ?? null,
    rows: [],
    busy: false,
  };
  const map = () => playable.find((m) => m.id === state.mapId);
  const firstPick = () => {
    const asked = opponents.find((p) => p.id === query.get("opponent") && p.ready);
    if (asked) return `player:${asked.id}`;
    return bots.some((b) => b.name === "wander") ? "bot:wander" : bots[0] ? `bot:${bots[0].name}` : "";
  };
  function setRows() {
    const free = (map()?.slots.length ?? 1) - 1;
    state.rows = Array.from({ length: free }, (_, i) => state.rows[i] ?? (i === 0 ? firstPick() : ""));
  }
  setRows();

  const mapGrid = h("div", { class: "map-grid pick" });
  const teamCard = h("section", { class: "card" });
  const opponentsCard = h("section", { class: "card" });
  const summary = h("section", { class: "card battle-summary" });

  root.append(
    battleTabs("skirmish"),
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Skirmish"),
        h("p", { class: "hint" }, "Choose a map, your tree and who to fight. The battle plays out at once; watch the replay afterwards."))),
    h("div", { class: "layout battle-layout" },
      h("div", { class: "side" },
        h("section", { class: "card" },
          h("div", { class: "card-head" }, h("h2", {}, "1. Map"), h("span", { class: "hint" }, "System maps, your own, and ones other players published")),
          mapGrid),
        teamCard, opponentsCard),
      h("aside", { class: "side" }, summary)));

  function renderMaps() {
    fill(mapGrid, playable.length ? playable.map((m) => h("button", {
      type: "button",
      class: `map-card${m.id === state.mapId ? " selected" : ""}`,
      onclick: () => { state.mapId = m.id; setRows(); render(); },
    },
    mapPreview(m, 200, 14),
    h("strong", {}, m.name),
    h("span", { class: "hint" }, `${m.width}×${m.height} · up to ${plural(m.slots.length, "team")}`)))
      : empty("There are no maps with room for two teams yet. Make one in Maps."));
  }

  function renderTeam() {
    const chosen = choices.find((c) => c.tree.name === state.tree);
    fill(teamCard,
      h("div", { class: "card-head" }, h("h2", {}, "2. Your tree"), h("a", { href: "#/trees" }, "Workshop")),
      choices.length ? h("select", {
        value: state.tree ?? "",
        onchange: (e) => { state.tree = e.target.value; render(); },
      },
      state.tree ? null : h("option", { value: "" }, "Choose a tree…"),
      h("optgroup", { label: "Your trees" }, choices.filter((c) => c.mine).map(option)),
      h("optgroup", { label: "Default trees" }, choices.filter((c) => !c.mine).map(option)))
        : empty("You have no trees yet."),
      chosen ? h("div", { class: "meter" },
        h("span", { style: `width:${Math.min(100, (100 * chosen.cost) / me.budget)}%` })) : null,
      h("p", { class: "hint" }, chosen ? `${chosen.cost} of your ${me.budget} points.` : "",
        " Trees over your budget, or not finished, can't fight."));
  }

  function option(c) {
    return h("option", { value: c.tree.name, disabled: Boolean(c.problem) },
      `${c.tree.name} · ${c.cost} points${c.problem ? ` (${c.problem})` : ""}`);
  }

  function renderOpponents() {
    const m = map();
    const takenPlayers = new Set(state.rows.filter((r) => r.startsWith("player:")));
    fill(opponentsCard,
      h("div", { class: "card-head" }, h("h2", {}, "3. Opponents"),
        h("span", { class: "hint" }, m ? `${plural(m.slots.length - 1, "slot")} to fill` : "")),
      state.rows.length ? h("div", { class: "opponent-rows" }, state.rows.map((value, i) =>
        h("label", { class: "opponent-row" },
          h("span", { class: "dot", style: `background:${slotColour(m.slots[i + 1])}` }),
          h("select", {
            value,
            onchange: (e) => { state.rows[i] = e.target.value; render(); },
          },
          h("option", { value: "" }, i === 0 ? "Choose an opponent…" : "Leave this slot empty"),
          h("optgroup", { label: "Players (they play their default tree)" }, opponents.map((p) =>
            h("option", {
              value: `player:${p.id}`,
              disabled: !p.ready || (takenPlayers.has(`player:${p.id}`) && value !== `player:${p.id}`),
            }, p.ready ? `${p.name} · level ${p.level} · ${p.treeCost}-point tree` : `${p.name} (no default tree yet)`))),
          h("optgroup", { label: "Practice bots (no XP for them)" }, bots.map((b) =>
            h("option", { value: `bot:${b.name}` }, `${b.name} · ${b.cost} points`))))))) : null,
      h("p", { class: "hint" }, "Every team gets the same agents. Only the trees differ."));
  }

  function renderSummary() {
    const m = map();
    const picked = state.rows.filter(Boolean);
    const names = { [m?.slots[0]]: `${me.name} (you)` };
    state.rows.forEach((value, i) => {
      if (!value) return;
      const [kind, id] = value.split(":");
      names[m.slots[i + 1]] = kind === "player" ? opponents.find((p) => p.id === id)?.name : `Bot (${id})`;
    });
    const criteria = (m?.criteria ?? []).filter((c) => !("slot" in c) || names[c.slot]);
    const ready = m && state.tree && picked.length && !state.busy;
    fill(summary,
      h("h2", {}, "Ready?"),
      m ? h("p", {}, h("strong", {}, m.name), ` · you start in slot ${m.slots[0]}`) : empty("Pick a map."),
      criteria.length ? h("ul", { class: "plain rules" },
        criteria.map((c) => h("li", {}, describeCriterion(c, (slot) => names[slot] ?? `Slot ${slot}`)))) : null,
      h("p", { class: "hint" }, "If nobody has won by the turn limit, the team with the most agents (then the most health) wins."),
      h("p", { class: "hint" }, `You get ${Math.round(factor * 100)}% of the XP your agents earn as account XP. `,
        "Players you fight get XP for their agents too."),
      h("button", { class: "primary big", disabled: !ready, onclick: fight }, state.busy ? "Fighting…" : "Fight"));
  }

  async function fight() {
    state.busy = true;
    renderSummary();
    try {
      const opponentsBody = state.rows.map((value, i) => {
        if (!value) return null;
        const [kind, id] = value.split(":");
        return { [kind]: id, slot: map().slots[i + 1] };
      }).filter(Boolean);
      const done = await post("/api/skirmish", {
        map: state.mapId, tree: state.tree, slot: map().slots[0], opponents: opponentsBody,
      });
      location.hash = `#/results/${done.gameId}`;
    } catch (e) {
      showError(e.problems?.length ? e.problems.join(" · ") : e.message);
      state.busy = false;
      renderSummary();
    }
  }

  function render() {
    renderMaps();
    renderTeam();
    renderOpponents();
    renderSummary();
  }
  render();
}
