// The top-level menu.

import { get } from "../api.js";
import { formatDate, h } from "../dom.js";

const MENU = [
  ["#/new", "New game", "Pick a map, choose how many teams play, and give each one a starting tree."],
  ["#/games", "Load game", "Open a saved game. It keeps its seed and starting setup, so it always plays out the same way."],
  ["#/trees", "Decision trees", "Build the trees your agents follow, a branch at a time, from dropdowns that only offer what fits."],
  ["#/maps", "Map editor", "Make and rename maps. Grow them tile by tile, then set height, food, plants, start slots and win conditions."],
  ["#/players", "Players", "The people who play. Each has a profile with their colour, starting tree, trees and games."],
  ["#/catalogue", "Catalogue", "Everything that's saved: maps, trees, players and games. Import old .map files here."],
];

export async function mount(root) {
  root.append(
    h("section", { class: "hero" },
      h("h1", {}, "War", h("span", {}, "Agents")),
      h("p", { class: "lede" },
        "Design the decision trees your agents follow, then watch the teams play it out. ",
        "Once a game starts you can't step in: the trees are the game.")),
    h("nav", { class: "menu" },
      MENU.map(([href, title, text]) =>
        h("a", { class: "menu-card", href }, h("strong", {}, title), h("span", {}, text)))));

  const games = await get("/api/catalogue/games");
  if (games.length) {
    root.append(h("section", { class: "card recent" },
      h("div", { class: "card-head" }, h("h2", {}, "Recent games"), h("a", { href: "#/games" }, "All saved games")),
      h("ul", { class: "plain" }, games.slice(0, 3).map((game) =>
        h("li", {},
          h("a", { href: `#/play/${game.id}` }, game.name),
          h("span", { class: "hint" }, ` · ${game.teams.map((t) => t.name).join(" vs ")} · ${formatDate(game.created)}`))))));
  }
}
