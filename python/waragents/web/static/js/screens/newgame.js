// Setting up a game: pick a map, then how many teams play, then each team's player, starting tree
// and stats. Starting it saves the game to the catalogue and opens it.

import { get, post } from "../api.js";
import { mapPreview } from "../board.js";
import { slotColour } from "../colours.js";
import { empty, fill, h, showError } from "../dom.js";

const STATS = [["speed", 10], ["health", 100], ["power", 10]];

// Words for a map's win conditions. teamName(slot) names the team in that slot.
export function describeCriterion(c, teamName) {
  switch (c.type) {
    case "SURVIVE_TURNS": return `The game ends after ${c.turns} turns`;
    case "ANNIHILATE": return `${teamName(c.slot)} wins by wiping out every other team, and loses if it's wiped out`;
    case "COLLECT_FOOD": return `${teamName(c.slot)} wins by picking up ${c.amount} food`;
    case "LEVEL_UP": return `${teamName(c.slot)} wins when an agent reaches ${c.exp} exp`;
    case "MAP_DIRT": return `The game ends when tile ${c.x}, ${c.y} reaches height ${c.dirt}`;
    case "TRAVEL_TO": return `${teamName(c.slot)} wins by reaching ${c.x}, ${c.y}`;
    case "PERFORM_ACTION": return `${teamName(c.slot)} wins by doing ${c.action} ${c.times} times`;
    case "FIND_THING": return `The first agent to find ${c.thing} wins`;
    default: return c.type;
  }
}

export async function mount(root, params, query) {
  const [maps, players, trees] = await Promise.all([
    get("/api/catalogue/maps"), get("/api/catalogue/players"), get("/api/catalogue/trees"),
  ]);
  const blocked = (m) => m.error ?? (m.problems?.length ? `Not playable yet: ${m.problems.join("; ")}` : null);
  const playable = maps.filter((m) => !blocked(m));
  const state = {
    mapId: null,
    teams: [],
    seed: "",
    name: "",
  };

  const map = () => maps.find((m) => m.id === state.mapId);
  const player = (id) => players.find((p) => p.id === id) ?? null;

  // The trees a player can start with: their own, then the defaults their own don't hide.
  function treesFor(playerId) {
    const own = trees.filter((t) => playerId && t.owner === playerId);
    const names = new Set(own.map((t) => t.name));
    const defaults = trees.filter((t) => t.owner === null && !names.has(t.name));
    return { own, defaults };
  }

  function defaultTree(playerId, avoid = []) {
    const { own, defaults } = treesFor(playerId);
    const ready = [...own, ...defaults].filter((t) => !t.problems?.length);
    return (ready.find((t) => !avoid.includes(t.id)) ?? ready[0])?.id ?? null;
  }

  // Choosing a player gives the team their colour and their starting tree, if it's ready.
  function setPlayer(team, playerId) {
    team.player = playerId;
    const chosen = player(playerId);
    if (chosen?.colour) team.colour = chosen.colour;
    const { own, defaults } = treesFor(playerId);
    const usable = [...own, ...defaults];
    const start = usable.find((t) => t.name === chosen?.startTree && !t.problems?.length);
    if (start) team.tree = start.id;
    else if (!usable.some((t) => t.id === team.tree)) team.tree = defaultTree(playerId);
  }

  function makeTeam(slot, index) {
    return {
      slot, player: null, tree: defaultTree(null, state.teams.map((t) => t.tree)),
      name: "", colour: slotColour(index + 1),
      ...Object.fromEntries(STATS),
    };
  }

  function chooseMap(mapId) {
    state.mapId = mapId;
    const slots = map().slots;
    state.teams = [];
    for (const [i, slot] of slots.slice(0, Math.min(2, slots.length)).entries()) {
      state.teams.push(makeTeam(slot, i));
    }
    // #/new?player=<id> comes from a player's page: their team goes first.
    const wanted = query.get("player");
    if (wanted && player(wanted) && state.teams.length) setPlayer(state.teams[0], wanted);
    render();
  }

  function setTeamCount(count) {
    const slots = map().slots;
    while (state.teams.length > count) state.teams.pop();
    while (state.teams.length < count) {
      const used = new Set(state.teams.map((t) => t.slot));
      state.teams.push(makeTeam(slots.find((s) => !used.has(s)), state.teams.length));
    }
    render();
  }

  // ---- rendering -------------------------------------------------------------------

  const mapsCard = h("section", { class: "card step" });
  const teamsCard = h("section", { class: "card step" });
  const rulesCard = h("section", { class: "card step" });
  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "New game"),
      h("p", { class: "hint" }, "Games are saved as soon as they start, so you can load them again later."))),
    mapsCard, teamsCard, rulesCard);

  function render() {
    renderMaps();
    renderTeams();
    renderRules();
  }

  function renderMaps() {
    mapsCard.replaceChildren(
      h("div", { class: "card-head" }, h("h2", {}, "1 · Map"),
        h("span", { class: "hint" }, "Numbered circles are start slots")),
      playable.length ? h("div", { class: "map-grid" }, maps.map((m) =>
        h("button", {
          class: `map-card${m.id === state.mapId ? " selected" : ""}`,
          disabled: Boolean(blocked(m)),
          title: blocked(m) ?? "",
          onclick: () => chooseMap(m.id),
        },
        m.error ? h("div", { class: "preview broken" }, "Can't load") : mapPreview(m, 200, 14),
        h("strong", {}, m.name),
        h("span", { class: "hint" }, blocked(m)
          ?? `${m.width}×${m.height} · ${m.slots.length} slot${m.slots.length === 1 ? "" : "s"} · ${m.plants.length} plant${m.plants.length === 1 ? "" : "s"}`))))
        : empty("There are no maps in the catalogue yet. Import a .map file in the Catalogue."));
  }

  function renderTeams() {
    const m = map();
    if (!m) {
      teamsCard.replaceChildren(h("div", { class: "card-head" }, h("h2", {}, "2 · Teams")), empty("Choose a map first."));
      return;
    }
    const counts = m.slots.map((_, i) => i + 1);
    fill(teamsCard,
      h("div", { class: "card-head" }, h("h2", {}, "2 · Teams"),
        h("label", { class: "inline" }, "Number of teams ",
          h("select", { value: String(state.teams.length), onchange: (e) => setTeamCount(Number(e.target.value)) },
            counts.map((n) => h("option", { value: String(n) }, String(n)))))),
      h("div", { class: "table-wrap" }, h("table", { class: "teams-table" },
        h("thead", {}, h("tr", {}, ["Slot", "Player", "Team name", "Colour", "Starting tree",
          ...STATS.map(([s]) => s[0].toUpperCase() + s.slice(1))].map((t) => h("th", {}, t)))),
        h("tbody", {}, state.teams.map((team, i) => teamRow(team, i, m))))),
      players.length ? null : h("p", { class: "hint" },
        "Every team uses the default trees. Add players on the Players screen to give them trees of their own."));
  }

  function teamRow(team, index, m) {
    const usedElsewhere = new Set(state.teams.filter((t) => t !== team).map((t) => t.slot));
    const { own, defaults } = treesFor(team.player);
    const treeOption = (t) => h("option", {
      value: t.id, disabled: Boolean(t.problems?.length),
    }, t.problems?.length ? `${t.name} (unfinished)` : t.name);
    const owner = player(team.player);
    return h("tr", {},
      h("td", {}, h("select", {
        value: String(team.slot),
        onchange: (e) => { team.slot = Number(e.target.value); render(); },
      }, m.slots.map((s) => h("option", { value: String(s), disabled: usedElsewhere.has(s) }, `Slot ${s}`)))),
      h("td", {}, h("select", {
        value: team.player ?? "",
        onchange: (e) => { setPlayer(team, e.target.value || null); render(); },
      }, h("option", { value: "" }, "None (default trees)"), players.map((p) => h("option", { value: p.id }, p.name)))),
      h("td", {}, h("input", {
        value: team.name, placeholder: owner?.name ?? `Team ${index + 1}`,
        oninput: (e) => { team.name = e.target.value; renderRules(); },
      })),
      h("td", {}, h("input", {
        type: "color", value: team.colour, oninput: (e) => { team.colour = e.target.value; },
      })),
      h("td", {}, h("select", {
        value: team.tree ?? "",
        onchange: (e) => { team.tree = e.target.value; },
      },
      own.length ? h("optgroup", { label: `${owner.name}'s trees` }, own.map(treeOption)) : null,
      h("optgroup", { label: "Default trees" }, defaults.map(treeOption)))),
      STATS.map(([stat]) => h("td", {}, h("input", {
        type: "number", min: "1", class: "stat", value: String(team[stat]),
        oninput: (e) => { team[stat] = Number(e.target.value); },
      }))));
  }

  function renderRules() {
    const m = map();
    if (!m) {
      rulesCard.replaceChildren(h("div", { class: "card-head" }, h("h2", {}, "3 · Start")));
      return;
    }
    const bySlot = new Map(state.teams.map((t, i) => [t.slot, t.name || player(t.player)?.name || `Team ${i + 1}`]));
    let criteria = m.criteria.filter((c) => c.slot === undefined || bySlot.has(c.slot));
    if (state.teams.length === 1) criteria = criteria.filter((c) => c.type !== "ANNIHILATE");
    const skipped = m.criteria.length - criteria.length;
    fill(rulesCard,
      h("div", { class: "card-head" }, h("h2", {}, "3 · Start")),
      h("h3", { class: "sub" }, "Win conditions"),
      criteria.length
        ? h("ul", { class: "plain criteria" }, criteria.map((c) => h("li", {}, describeCriterion(c, (s) => bySlot.get(s)))))
        : empty("None, so the game runs until no agents are left."),
      skipped ? h("p", { class: "hint" },
        `${skipped} condition${skipped === 1 ? " is" : "s are"} left out because ${skipped === 1 ? "it's" : "they're"} about slots no team is using` +
        (state.teams.length === 1 ? " or about wiping out other teams." : ".")) : null,
      h("div", { class: "form-row" },
        h("label", {}, "Seed ", h("input", {
          type: "number", min: "0", placeholder: "random", value: state.seed,
          oninput: (e) => { state.seed = e.target.value; },
        })),
        h("label", { class: "grow" }, "Game name ", h("input", {
          placeholder: `${m.name} · today`, value: state.name,
          oninput: (e) => { state.name = e.target.value; },
        })),
        h("button", { class: "primary", onclick: start }, "Start game")),
      h("p", { class: "hint" }, "The same map, teams and seed always play out the same way."));
  }

  async function start() {
    showError("");
    const seedText = String(state.seed).trim();
    try {
      const game = await post("/api/games", {
        map: state.mapId,
        seed: seedText === "" ? null : Number(seedText),
        name: state.name.trim() || null,
        teams: state.teams,
      });
      location.hash = `#/play/${game.id}`;
    } catch (e) {
      showError(e.message);
    }
  }

  const preferred = query.get("map") ?? (playable.find((m) => m.id === "skirmish") ?? playable[0])?.id;
  if (preferred && playable.some((m) => m.id === preferred)) chooseMap(preferred);
  else render();
}
