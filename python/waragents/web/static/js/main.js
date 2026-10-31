// The app shell: a hash router that mounts one screen at a time into <main id="view">.
//
// Each screen module exports mount(root, params, query). It can return (or resolve to) a cleanup
// function, which runs when the user leaves the screen. Every screen but #/login needs someone
// signed in; anyone else is sent to sign in and brought back afterwards.

import { $, fill, h, showError } from "./dom.js";
import * as account from "./screens/account.js";
import * as analytics from "./screens/analytics.js";
import * as battle from "./screens/battle.js";
import * as catalogue from "./screens/catalogue.js";
import * as friends from "./screens/friends.js";
import * as guide from "./screens/guide.js";
import * as history from "./screens/history.js";
import * as home from "./screens/home.js";
import * as login from "./screens/login.js";
import * as maps from "./screens/maps.js";
import * as newGame from "./screens/newgame.js";
import * as play from "./screens/play.js";
import * as players from "./screens/players.js";
import * as results from "./screens/results.js";
import * as season from "./screens/season.js";
import * as training from "./screens/training.js";
import * as trees from "./screens/trees.js";
import { isAdmin, loadUser, signOut, user } from "./session.js";

const ROUTES = [
  { pattern: /^\/?$/, screen: home, section: null, title: "" },
  { pattern: /^\/login$/, screen: login, section: "login", title: "Sign in", open: true },
  { pattern: /^\/training(?:\/([\w-]+)(?:\/watch\/([\w-]+))?)?$/, screen: training, section: "training", title: "Training" },
  { pattern: /^\/battle$/, screen: battle, section: "battle", title: "Battle" },
  { pattern: /^\/season(?:\/([\w-]+))?$/, screen: season, section: "battle", title: "Season" },
  { pattern: /^\/results\/([\w-]+)$/, screen: results, section: "history", title: "Result" },
  { pattern: /^\/history$/, screen: history, section: "history", title: "History" },
  { pattern: /^\/analytics$/, screen: analytics, section: "analytics", title: "Analytics" },
  { pattern: /^\/play\/([\w-]+)$/, screen: play, section: "history", title: "Replay" },
  { pattern: /^\/sandbox$/, screen: newGame, section: "battle", title: "Sandbox" },
  { pattern: /^\/trees(?:\/([\w-]+))?$/, screen: trees, section: "trees", title: "Workshop" },
  { pattern: /^\/maps(?:\/([\w-]+))?$/, screen: maps, section: "maps", title: "Maps" },
  { pattern: /^\/account$/, screen: account, section: "account", title: "Your account" },
  { pattern: /^\/players(?:\/([\w-]+))?$/, screen: players, section: "players", title: "Players" },
  { pattern: /^\/friends$/, screen: friends, section: "friends", title: "Friends" },
  { pattern: /^\/guide$/, screen: guide, section: "guide", title: "Guide" },
  { pattern: /^\/catalogue(?:\/(\w+))?$/, screen: catalogue, section: "catalogue", title: "Catalogue" },
];

// Old addresses, so bookmarks still work.
const MOVED = { "/new": "#/sandbox", "/games": "#/history" };

let cleanup = null;
let generation = 0;
let loading = null;

// The signed-in player's name in the top bar, with Sign out. Admins also see the Catalogue link.
function renderAccount() {
  const me = user();
  $("account").hidden = $("nav").hidden = !me;
  for (const link of document.querySelectorAll("[data-admin]")) link.hidden = !isAdmin();
  if (!me) return;
  // How many friend requests are waiting for an answer.
  fill($("nav-friends"), "Friends", me.friendRequests
    ? h("span", { class: "badge count", title: `${me.friendRequests} friend request(s) waiting for you` }, me.friendRequests) : null);
  fill($("account"),
    h("a", { href: "#/account", class: "account-name", title: "Your account" },
      h("span", { class: "dot", style: me.colour ? `background:${me.colour}` : "" }), me.name,
      h("span", { class: "badge level-badge" }, `Lv ${me.level}`)),
    h("button", {
      class: "small",
      onclick: async () => {
        await signOut();
        location.hash = "#/login";
      },
    }, "Sign out"));
}

async function route() {
  const [path, queryString = ""] = location.hash.replace(/^#/, "").split("?");
  const query = new URLSearchParams(queryString);
  if (MOVED[path]) {
    location.replace(`${MOVED[path]}${queryString ? `?${queryString}` : ""}`);
    return;
  }
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

  // Check again on the sign-in screen: we may have been sent there because the session ended.
  if (route.open) loading = null;
  loading ??= loadUser().catch((e) => { loading = null; throw e; });
  try {
    await loading;
  } catch (e) {
    showError(`Can't reach the server: ${e.message}`);
    return;
  }
  if (current !== generation) return;
  renderAccount();
  if (!user() && !route.open) {
    location.replace(`#/login?next=${encodeURIComponent(location.hash || "#/")}`);
    return;
  }
  if (user() && route.screen === login) {
    location.replace(query.get("next") || "#/");
    return;
  }

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
window.addEventListener("waragents:user", renderAccount);
route();
