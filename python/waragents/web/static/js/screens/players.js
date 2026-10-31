// Players (#/players, admins only) and a player's public profile (#/players/<id>, anyone): their
// level, whether they can be picked to fight, how you stand as friends, and the games you've
// played together. Trees stay private. Your own settings are on the Account screen, and the
// players you know are on the Friends screen.

import { get } from "../api.js";
import { empty, fill, formatDate, formatDay, h } from "../dom.js";
import { modeBadge, placeText } from "../format.js";
import { avatar, friendControls } from "../people.js";
import { isAdmin, user } from "../session.js";

// Everyone, with the level and readiness /api/opponents gives for players other than you.
async function everyone() {
  const [players, opponents] = await Promise.all([get("/api/catalogue/players"), get("/api/opponents")]);
  const me = user();
  return players.map((p) => p.id === me.id
    ? { ...p, level: me.level, ready: me.defaultTree.ready, you: true }
    : { ...p, ...opponents.find((o) => o.id === p.id) });
}

async function list(root) {
  if (!isAdmin()) throw new Error("Only admins can see every player. Your friends are on the Friends screen.");
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
      h("p", { class: "hint" }, "Everyone who plays. Only admins see this list."))),
    h("section", { class: "card" },
      players.length ? h("div", { class: "player-grid" }, players.map(card)) : empty("No players yet.")));
}

async function profile(root, playerId) {
  const [player, history] = await Promise.all([get(`/api/players/${playerId}`), get("/api/history")]);
  const together = history.filter((g) => g.teams.some((t) => t.player === playerId));
  const me = user();
  const actions = h("div", { class: "head-actions" });

  async function drawActions() {
    Object.assign(player, await get(`/api/players/${playerId}`));
    fill(actions,
      isAdmin() ? h("a", { class: "button", href: "#/players" }, "All players") : h("a", { class: "button", href: "#/friends" }, "Friends"),
      player.you ? h("a", { class: "button primary", href: "#/account" }, "Edit your account") : friendControls(player, drawActions),
      !player.you && player.ready ? h("a", { class: "button", href: `#/battle?opponent=${playerId}` }, `Fight ${player.name}`) : null);
  }

  root.append(
    h("div", { class: "page-head" },
      h("div", { class: "player-head" }, avatar(player, true), h("div", {},
        h("h1", {}, player.name),
        h("p", { class: "hint" }, `Level ${player.level ?? 1}`, player.created ? ` · joined ${formatDay(player.created)}` : ""))),
      actions),
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
  await drawActions();
}

export async function mount(root, [playerId]) {
  return playerId ? profile(root, playerId) : list(root);
}
