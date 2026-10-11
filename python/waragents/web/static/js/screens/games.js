// Load game: the saved games, newest first.

import { get, remove } from "../api.js";
import { PALETTE } from "../colours.js";
import { empty, formatDate, h, showError } from "../dom.js";

// The saved-games table, also used by the catalogue. onChange runs after a delete.
export function gameList(games, onChange) {
  if (!games.length) {
    return empty("No saved games yet. Games are saved when you start them from New game.");
  }
  return h("div", { class: "table-wrap" }, h("table", { class: "list" },
    h("thead", {}, h("tr", {}, ["Game", "Map", "Teams", "Seed", "Started", ""].map((t) => h("th", {}, t)))),
    h("tbody", {}, games.map((game) => h("tr", {},
      h("td", {}, h("a", { href: `#/play/${game.id}` }, game.name)),
      h("td", {}, game.mapName ?? game.mapId ?? "?"),
      h("td", {}, game.error ? h("span", { class: "error-text" }, game.error) : h("span", { class: "team-list" },
        (game.teams ?? []).map((team, i) => h("span", { class: "team-tag", title: `Slot ${team.slot} · starts with ${team.startTree}` },
          h("span", { class: "dot", style: `background:${team.colour ?? PALETTE[i % PALETTE.length]}` }), team.name)))),
      h("td", { class: "num" }, game.seed ?? ""),
      h("td", {}, formatDate(game.created)),
      h("td", { class: "actions" },
        h("a", { class: "button small", href: `#/play/${game.id}` }, "Open"),
        h("button", {
          class: "small danger",
          onclick: async () => {
            if (!confirm(`Delete the saved game "${game.name}"?`)) return;
            try {
              await remove(`/api/catalogue/games/${game.id}`);
              onChange();
            } catch (e) {
              showError(e.message);
            }
          },
        }, "Delete")))))));
}

export async function mount(root) {
  const body = h("section", { class: "card" });
  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Load game"),
      h("p", { class: "hint" },
        "A game carries on from where you left it, and Reset takes it back to turn 0. ",
        "It keeps its seed and starting setup, so it always plays out the same way.")),
    h("div", { class: "head-actions" }, h("a", { class: "button primary", href: "#/new" }, "New game"))),
    body);
  async function refresh() {
    body.replaceChildren(gameList(await get("/api/catalogue/games"), refresh));
  }
  await refresh();
}
