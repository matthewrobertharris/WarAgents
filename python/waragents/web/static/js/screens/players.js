// Players (#/players) and a player's public profile (#/players/<id>): their level, whether they
// can be picked to fight, and the games you've played together. Trees stay private. Your own
// settings are on the Account screen.

import { get } from "../api.js";
import { PALETTE } from "../colours.js";
import { empty, formatDate, formatDay, h } from "../dom.js";
import { modeBadge, placeText } from "../format.js";
import { user } from "../session.js";

const initials = (name) => (name ?? "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";

function avatar(player, big = false) {
  return h("span", { class: `avatar${big ? " big" : ""}`, style: `background:${player.colour ?? PALETTE[6]}` }, initials(player.name));
}

// Everyone, with the level and readiness /api/opponents gives for players other than you.
async function everyone() {
  const [players, opponents] = await Promise.all([get("/api/catalogue/players"), get("/api/opponents")]);
  const me = user();
  return players.map((p) => p.id === me.id
    ? { ...p, level: me.level, ready: me.defaultTree.ready, you: true }
    : { ...p, ...opponents.find((o) => o.id === p.id) });
}

async function list(root) {
  const players = await everyone();
  const card = (p) => h("a", { class: "player-card", href: `#/players/${p.id}` },
    avatar(p),
    h("span", { class: "who" },
      h("strong", {}, p.name, p.you ? h("span", { class: "hint" }, " (you)") : null),
      h("span", { class: "hint" }, `Level ${p.level ?? 1}`, p.created ? ` · joined ${formatDay(p.created)}` : ""),
      p.ready ? h("span", { class: "badge ok" }, "ready to fight") : h("span", { class: "badge" }, "no default tree")));
  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Players"),
      h("p", { class: "hint" }, "Everyone who plays. Pick someone ready to fight from their profile, or in Battle."))),
    h("section", { class: "card" },
      players.length ? h("div", { class: "player-grid" }, players.map(card)) : empty("No players yet.")));
}

async function profile(root, playerId) {
  const [players, history] = await Promise.all([everyone(), get("/api/history")]);
  const player = players.find((p) => p.id === playerId);
  if (!player) throw new Error(`There's no player called '${playerId}'`);
  const together = history.filter((g) => g.teams.some((t) => t.player === playerId));
  const me = user();

  root.append(
    h("div", { class: "page-head" },
      h("div", { class: "player-head" }, avatar(player, true), h("div", {},
        h("h1", {}, player.name),
        h("p", { class: "hint" }, `Level ${player.level ?? 1}`, player.created ? ` · joined ${formatDay(player.created)}` : ""))),
      h("div", { class: "head-actions" },
        h("a", { class: "button", href: "#/players" }, "All players"),
        player.you ? h("a", { class: "button primary", href: "#/account" }, "Edit your account")
          : player.ready ? h("a", { class: "button primary", href: `#/battle?opponent=${playerId}` }, `Fight ${player.name}`)
            : null)),
    h("div", { class: "layout player-layout" },
      h("section", { class: "card" },
        h("h2", {}, player.you ? "Your games" : "Games together"),
        together.length ? h("ul", { class: "plain recent-list" }, together.slice(0, 20).map((g) => h("li", {},
          modeBadge(g.mode),
          h("a", { href: g.finished ? `#/results/${g.id}` : `#/play/${g.id}` }, g.name),
          h("span", { class: "hint" }, ` ${g.finished ? placeText(g.place, g.teamCount, g.winners) : ""} · ${formatDate(g.created)}`))))
          : empty(player.you ? "No games yet." : `You haven't played ${player.name} yet.`)),
      h("aside", { class: "side" },
        h("section", { class: "card" },
          h("h2", {}, "Default tree"),
          h("p", {}, player.ready
            ? (player.you ? `Ready: ${me.defaultTree.name}, ${me.defaultTree.cost} points.` : `Ready, and it costs ${player.treeCost} points.`)
            : "Not ready, so they can't be picked to fight yet."),
          h("p", { class: "hint" }, "Players' trees are private. You only see what their agents do in battle.")))));
}

export async function mount(root, [playerId]) {
  return playerId ? profile(root, playerId) : list(root);
}
