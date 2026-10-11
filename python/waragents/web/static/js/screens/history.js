// History (#/history): every game you started or had a team in, newest first. Finished games open
// their result; games still going (sandbox) open in the viewer.

import { get } from "../api.js";
import { teamColour } from "../colours.js";
import { empty, fill, formatDate, h } from "../dom.js";
import { MODES, modeBadge, placeText } from "../format.js";
import { user } from "../session.js";

export async function mount(root) {
  const games = await get("/api/history");
  const me = user();
  let filter = "all";
  const counts = Object.fromEntries(Object.keys(MODES).map((m) => [m, games.filter((g) => g.mode === m).length]));
  const tabs = h("div", { class: "tabs big" });
  const list = h("div", { class: "table-wrap" });

  function render() {
    fill(tabs, [["all", `All (${games.length})`], ...Object.entries(MODES).filter(([m]) => counts[m])
      .map(([m, info]) => [m, `${info.label} (${counts[m]})`])]
      .map(([value, label]) => h("button", {
        class: `tab${filter === value ? " current" : ""}`,
        onclick: () => { filter = value; render(); },
      }, label)));
    const shown = games.filter((g) => filter === "all" || g.mode === filter);
    fill(list, shown.length ? h("table", { class: "history" },
      h("thead", {}, h("tr", {}, ["When", "Mode", "Game", "Teams", "You", "XP", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, shown.map((g) => {
        const href = g.finished ? `#/results/${g.id}` : `#/play/${g.id}`;
        return h("tr", { class: g.finished && !g.seen ? "unseen" : "" },
          h("td", { class: "hint" }, formatDate(g.created)),
          h("td", {}, modeBadge(g.mode)),
          h("td", {}, h("a", { href }, g.name), g.finished && !g.seen ? h("span", { class: "badge warn" }, "new") : null),
          h("td", {}, h("span", { class: "team-dots" }, g.teams.map((t) =>
            h("span", { class: "dot", title: t.name, style: `background:${teamColour(g.teams, t.name)}` }))),
          " ", g.teams.map((t) => (t.player === me.id ? "You" : t.name)).join(" vs ")),
          h("td", {}, g.finished ? placeText(g.place, g.teamCount, g.winners) : h("span", { class: "hint" }, "not finished")),
          h("td", { class: "num" }, g.xp ? `+${g.xp}` : ""),
          h("td", {}, h("a", { class: "button small", href: `#/play/${g.id}` }, g.finished ? "Replay" : "Open")));
      })))
      : empty(games.length ? "No games of this kind." : "No games yet. Try Training, or pick a fight in Battle."));
  }

  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "History"),
        h("p", { class: "hint" }, "Every game replays exactly as it happened, from its seed and starting setup."))),
    h("section", { class: "card" }, tabs, list));
  render();
}
