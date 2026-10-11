// The app shell: a hash router that mounts one screen at a time into <main id="view">.
//
// Each screen module exports mount(root, params, query). It can return (or resolve to) a cleanup
// function, which runs when the user leaves the screen.

import { $, showError } from "./dom.js";
import * as catalogue from "./screens/catalogue.js";
import * as games from "./screens/games.js";
import * as home from "./screens/home.js";
import * as maps from "./screens/maps.js";
import * as newGame from "./screens/newgame.js";
import * as play from "./screens/play.js";
import * as players from "./screens/players.js";
import * as trees from "./screens/trees.js";

const ROUTES = [
  { pattern: /^\/?$/, screen: home, section: null, title: "" },
  { pattern: /^\/new$/, screen: newGame, section: "new", title: "New game" },
  { pattern: /^\/games$/, screen: games, section: "games", title: "Load game" },
  { pattern: /^\/play\/([\w-]+)$/, screen: play, section: "games", title: "Game" },
  { pattern: /^\/trees(?:\/([\w-]+))?$/, screen: trees, section: "trees", title: "Decision trees" },
  { pattern: /^\/maps(?:\/([\w-]+))?$/, screen: maps, section: "maps", title: "Map editor" },
  { pattern: /^\/catalogue(?:\/(\w+))?$/, screen: catalogue, section: "catalogue", title: "Catalogue" },
  { pattern: /^\/players(?:\/([\w-]+))?$/, screen: players, section: "players", title: "Players" },
];

let cleanup = null;
let generation = 0;

async function route() {
  const [path, queryString = ""] = location.hash.replace(/^#/, "").split("?");
  const query = new URLSearchParams(queryString);
  let match = null;
  let route = ROUTES[0];
  for (const candidate of ROUTES) {
    match = path.match(candidate.pattern);
    if (match) {
      route = candidate;
      break;
    }
  }

  cleanup?.();
  cleanup = null;
  showError("");
  const current = ++generation;
  for (const link of $("nav").querySelectorAll("a")) {
    link.classList.toggle("active", link.dataset.section === route.section);
  }
  document.title = route.title ? `${route.title} · WarAgents` : "WarAgents";

  // A fresh container per visit, so a slow screen that finishes loading after the user has left
  // only writes into a detached element.
  const root = document.createElement("div");
  root.className = `screen screen-${route.section ?? "home"}`;
  $("view").replaceChildren(root);
  if (!match) {
    showError(`There's no page at #${path}`);
  }
  try {
    const done = await route.screen.mount(root, match ? match.slice(1) : [], query);
    if (current === generation) cleanup = done ?? null;
    else done?.();
  } catch (e) {
    if (current === generation) showError(e.message);
  }
}

window.addEventListener("hashchange", route);
route();
