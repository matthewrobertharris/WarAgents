// Players: everyone who plays (#/players), and one player's page (#/players/<id>). A player is
// treated like an account: their name and colour, the tree their teams start with, the trees
// they own, the games they've played in, and deleting them.

import { get, post, put, remove } from "../api.js";
import { PALETTE } from "../colours.js";
import { empty, fill, formatDate, formatDay, h, showError } from "../dom.js";
import { countNodes, fromJson } from "../treeview.js";
import { gameList } from "./games.js";
import { freeName, status } from "./trees.js";

const initials = (name) => (name ?? "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";

function avatar(player, big = false) {
  return h("span", { class: `avatar${big ? " big" : ""}`, style: `background:${player.colour ?? PALETTE[6]}` }, initials(player.name));
}

const gamesOf = (games, playerId) => games.filter((g) => g.teams?.some((t) => t.player === playerId));
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// ---- the list ----------------------------------------------------------------------

async function list(root) {
  const [players, trees, games] = await Promise.all([
    get("/api/catalogue/players"), get("/api/catalogue/trees"), get("/api/catalogue/games"),
  ]);

  const used = new Set(players.map((p) => p.colour));
  const name = h("input", { placeholder: "Name", required: true, autocomplete: "off" });
  const colour = h("input", { type: "color", value: PALETTE.find((c) => !used.has(c)) ?? PALETTE[0] });
  const add = h("form", {
    class: "form-row add-player",
    onsubmit: async (e) => {
      e.preventDefault();
      try {
        const made = await post("/api/catalogue/players", { name: name.value.trim(), colour: colour.value, startTree: null });
        location.hash = `#/players/${made.id}`;
      } catch (err) {
        showError(err.message);
      }
    },
  }, h("label", { class: "grow" }, "Name ", name), h("label", {}, "Colour ", colour),
  h("button", { class: "primary" }, "Add player"));

  const card = (p) => {
    const played = gamesOf(games, p.id);
    const owned = trees.filter((t) => t.owner === p.id).length;
    return h("a", { class: "player-card", href: `#/players/${p.id}` },
      avatar(p),
      h("span", { class: "who" },
        h("strong", {}, p.name),
        h("span", { class: "hint" }, `${plural(owned, "tree")} · ${plural(played.length, "game")}`),
        h("span", { class: "hint" }, played.length ? `Last played ${formatDate(played[0].created)}`
          : p.created ? `Joined ${formatDay(p.created)}` : "")));
  };

  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Players"),
      h("p", { class: "hint" },
        "A player is a person, like an account. Their trees are theirs alone, and their teams take their colour."))),
    h("section", { class: "card" },
      h("div", { class: "card-head" }, h("h2", {}, "Everyone")),
      players.length ? h("div", { class: "player-grid" }, players.map(card))
        : empty("No players yet. Without one, every team uses the default trees."),
      add));
  name.focus();
}

// ---- one player --------------------------------------------------------------------

async function profile(root, playerId) {
  const [loaded, trees, games] = await Promise.all([
    get(`/api/catalogue/players/${playerId}`), get("/api/catalogue/trees"), get("/api/catalogue/games"),
  ]);
  const { id, ...rest } = loaded;
  const player = { name: "", colour: PALETTE[0], startTree: null, ...rest };
  const mine = trees.filter((t) => t.owner === playerId);
  const ownNames = new Set(mine.map((t) => t.name));
  const defaults = trees.filter((t) => t.owner === null && !ownNames.has(t.name));
  const played = gamesOf(games, playerId);

  const savedNote = h("span", { class: "hint save-status" });
  async function save(changes) {
    const next = { ...player, ...changes };
    savedNote.textContent = "Saving…";
    try {
      await put(`/api/catalogue/players/${playerId}`, next);
      Object.assign(player, changes);
      savedNote.textContent = "Saved";
    } catch (e) {
      savedNote.textContent = "Not saved";
      showError(e.message);
    }
    renderHead();
  }

  // Header: avatar, name and joined date. Redrawn when the name or colour changes.
  const head = h("div", { class: "page-head" });
  function renderHead(preview = {}) {
    const shown = { ...player, ...preview };
    fill(head,
      h("div", { class: "player-head" }, avatar(shown, true), h("div", {},
        h("h1", {}, shown.name || "Unnamed"),
        h("p", { class: "hint" }, player.created ? `Player since ${formatDay(player.created)} · ` : "", `id ${playerId}`))),
      h("div", { class: "head-actions" },
        h("a", { class: "button", href: "#/players" }, "All players"),
        h("a", { class: "button primary", href: `#/new?player=${playerId}` }, "New game")));
  }
  renderHead();

  // Profile: name, colour and starting tree.
  const name = h("input", {
    value: player.name, autocomplete: "off",
    oninput: () => renderHead({ name: name.value }),
    onchange: () => {
      const value = name.value.trim();
      if (!value) {
        showError("A player needs a name");
        name.value = player.name;
        renderHead();
        return;
      }
      if (value !== player.name) save({ name: value });
    },
  });
  const colour = h("input", {
    type: "color", value: player.colour,
    oninput: () => renderHead({ colour: colour.value }),
    onchange: () => save({ colour: colour.value }),
  });
  const swatches = h("span", { class: "swatches" }, PALETTE.map((c) => h("button", {
    type: "button", class: "colour-swatch", title: c, style: `background:${c}`,
    onclick: () => { colour.value = c; save({ colour: c }); },
  })));

  const treeOption = (t) => h("option", { value: t.name },
    t.problems?.length ? `${t.name} (unfinished)` : t.name);
  const known = [...mine, ...defaults].some((t) => t.name === player.startTree);
  const startHint = h("p", { class: "hint" });
  const startTree = h("select", {
    value: player.startTree ?? "",
    onchange: () => { save({ startTree: startTree.value || null }); describeStart(); },
  },
  h("option", { value: "" }, "None (pick one each game)"),
  player.startTree && !known ? h("option", { value: player.startTree }, `${player.startTree} (missing)`) : null,
  mine.length ? h("optgroup", { label: "Their trees" }, mine.map(treeOption)) : null,
  h("optgroup", { label: "Default trees" }, defaults.map(treeOption)));
  function describeStart() {
    const chosen = [...mine, ...defaults].find((t) => t.name === startTree.value);
    startHint.textContent = !startTree.value ? "New game picks a tree for their teams, and you can change it there."
      : !chosen ? "There's no tree with this name any more, so New game will pick another."
        : chosen.problems?.length ? "This tree isn't finished, so New game will pick another until it is."
          : "Their teams start with this tree unless you choose another in New game.";
  }
  describeStart();

  const profileCard = h("section", { class: "card" },
    h("div", { class: "card-head" }, h("h2", {}, "Profile"), savedNote),
    h("div", { class: "fields" },
      h("label", {}, "Name", name),
      h("p", { class: "hint" }, `Renaming keeps the id ${playerId}, so their trees and games still point here.`),
      h("label", {}, "Colour", h("span", { class: "colour-pick" }, colour, swatches)),
      h("p", { class: "hint" }, "Their teams get this colour in New game."),
      h("label", {}, "Starting tree", startTree),
      startHint));

  // Trees they own.
  async function newTree() {
    try {
      const made = await post("/api/catalogue/trees", { name: freeName(trees, playerId, "new-tree"), owner: playerId, root: null });
      location.hash = `#/trees/${made.id}?new=1`;
    } catch (e) {
      showError(e.message);
    }
  }
  const treesCard = h("section", { class: "card" },
    h("div", { class: "card-head" }, h("h2", {}, "Trees"), h("button", { class: "small", onclick: newTree }, "New tree")),
    mine.length ? h("ul", { class: "tree-list" }, mine.map((tree) => h("li", {},
      h("a", { href: `#/trees/${tree.id}` }, h("strong", {}, tree.name)),
      h("span", { class: "hint" }, plural(tree.root ? countNodes(fromJson(tree.root)) : 0, "node")),
      tree.name === player.startTree ? h("span", { class: "hint" }, "starting tree") : null,
      status(tree),
      h("span", { class: "row-actions" }, h("a", { class: "button small", href: `#/trees/${tree.id}` }, "Edit")))))
      : empty("None of their own yet."),
    h("p", { class: "hint" },
      `They can also use the ${plural(defaults.length, "default tree")}. One of their own with the same name as a default hides it.`));

  const refresh = () => { root.replaceChildren(); return profile(root, playerId); };
  const gamesCard = h("section", { class: "card" },
    h("div", { class: "card-head" }, h("h2", {}, "Games"), h("span", { class: "hint" }, "Games where one of the teams is theirs")),
    played.length ? gameList(played, refresh) : empty("No games yet."));

  // Summary and deleting.
  const summary = h("section", { class: "card" },
    h("h2", {}, "Summary"),
    h("dl", { class: "stats" },
      h("dt", {}, "Joined"), h("dd", {}, player.created ? formatDay(player.created) : "unknown"),
      h("dt", {}, "Trees"), h("dd", {}, mine.length),
      h("dt", {}, "Games"), h("dd", {}, played.length),
      h("dt", {}, "Last played"), h("dd", {}, played.length ? formatDate(played[0].created) : "never")));

  async function deletePlayer() {
    const also = mine.length ? ` and their ${plural(mine.length, "tree")} (${mine.map((t) => t.name).join(", ")})` : "";
    if (!confirm(`Delete ${player.name}${also}? Saved games keep their own copies. This can't be undone.`)) return;
    try {
      for (const tree of mine) await remove(`/api/catalogue/trees/${tree.id}`);
      await remove(`/api/catalogue/players/${playerId}`);
      location.hash = "#/players";
    } catch (e) {
      showError(e.message);
    }
  }
  const danger = h("section", { class: "card danger-zone" },
    h("h2", {}, "Delete player"),
    h("p", { class: "hint" }, mine.length
      ? `Deletes ${player.name} and the ${plural(mine.length, "tree")} they own. Saved games keep their own copies.`
      : `Deletes ${player.name}. Saved games keep their own copies.`),
    h("button", { class: "danger", onclick: deletePlayer }, mine.length ? `Delete ${player.name} and their trees` : `Delete ${player.name}`));

  root.append(head, h("div", { class: "layout player-layout" },
    h("div", { class: "side" }, profileCard, treesCard, gamesCard),
    h("div", { class: "side" }, summary, danger)));
}

export async function mount(root, [playerId]) {
  return playerId ? profile(root, playerId) : list(root);
}
