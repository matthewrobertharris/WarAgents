// Season (#/season): ranked battles on generated maps, the leaderboard, and past seasons
// (#/season/<id>). Pick a tree and the server finds you opponents with trees of a similar cost and
// a similar rating. Admins start and end seasons here.

import { get, post, reference } from "../api.js";
import { teamCost, usableTrees } from "../cost.js";
import { empty, fill, formatDay, h, showError } from "../dom.js";
import { battleTabs, ordinal, plural } from "../format.js";
import { isAdmin, user } from "../session.js";

function leaderboardTable(rows, me) {
  return rows.length ? h("div", { class: "table-wrap" }, h("table", { class: "leaderboard" },
    h("thead", {}, h("tr", {}, ["", "Player", "Level", "Rating", "Battles", "Wins"].map((t) => h("th", {}, t)))),
    h("tbody", {}, rows.map((r) => h("tr", { class: r.player === me.id ? "me" : "" },
      h("td", { class: "place" }, ordinal(r.rank)),
      h("td", {}, h("span", { class: "dot", style: r.colour ? `background:${r.colour}` : "" }), " ",
        h("a", { href: `#/players/${r.player}` }, r.name), r.player === me.id ? h("span", { class: "hint" }, " (you)") : null),
      h("td", { class: "num" }, r.level),
      h("td", { class: "num" }, Math.round(r.rating)),
      h("td", { class: "num" }, r.games),
      h("td", { class: "num" }, r.wins))))))
    : empty("Nobody has fought in this season yet.");
}

async function pastSeason(root, seasonId) {
  const season = await get(`/api/season/${seasonId}`);
  const me = user();
  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, season.name),
        h("p", { class: "hint" }, `${formatDay(season.started)} to ${formatDay(season.ended)} · final standings`)),
      h("div", { class: "head-actions" }, h("a", { class: "button", href: "#/season" }, "Season"))),
    ...(season.standings ?? []).map((band) => h("section", { class: "card" },
      h("h2", {}, band.label),
      h("table", { class: "leaderboard" },
        h("thead", {}, h("tr", {}, ["In band", "Player", "Level", "Rating", "Battles", "Reward"].map((t) => h("th", {}, t)))),
        h("tbody", {}, band.players.map((p) => h("tr", { class: p.player === me.id ? "me" : "" },
          h("td", { class: "place" }, p.bandRank ? ordinal(p.bandRank) : "–"),
          h("td", {}, p.name),
          h("td", { class: "num" }, p.level),
          h("td", { class: "num" }, Math.round(p.rating)),
          h("td", { class: "num" }, p.games),
          h("td", { class: "num" }, p.reward ? `+${p.reward} XP` : h("span", { class: "hint" }, "too few battles")))))))));
}

export async function mount(root, [seasonId]) {
  if (seasonId) return pastSeason(root, seasonId);
  const [data, trees, ref] = await Promise.all([get("/api/season"), get("/api/catalogue/trees"), reference()]);
  const me = user();
  const season = data.current;
  const p = ref.progression;
  let filter = "all";
  let busy = false;

  const usable = usableTrees(trees, me.id);
  const choices = Object.values(usable).map((t) => {
    const cost = teamCost(t, usable, ref).cost;
    return { t, cost, ok: !t.problems?.length && cost <= me.budget };
  }).filter((c) => c.ok).sort((a, b) => (b.t.owner === me.id) - (a.t.owner === me.id) || b.cost - a.cost);
  let tree = choices.find((c) => c.t.name === me.startTree)?.t.name ?? choices[0]?.t.name ?? null;

  async function fight() {
    busy = true;
    renderFight();
    try {
      const done = await post("/api/season/battle", { tree });
      location.hash = `#/results/${done.gameId}`;
    } catch (e) {
      showError(e.message);
      busy = false;
      renderFight();
    }
  }

  const fightCard = h("section", { class: "card season-fight" });
  function renderFight() {
    const mine = season?.me;
    fill(fightCard,
      h("h2", {}, "Your season"),
      mine ? h("dl", { class: "stats" },
        h("dt", {}, "Rank"), h("dd", {}, `${ordinal(mine.rank)} of ${season.leaderboard.length}`),
        h("dt", {}, "Rating"), h("dd", {}, Math.round(mine.rating)),
        h("dt", {}, "Battles"), h("dd", {}, `${mine.games} (${plural(mine.wins, "win")})`))
        : h("p", { class: "hint" }, `You haven't fought this season yet. Everyone starts with a rating of 1000.`),
      choices.length ? h("label", { class: "stacked" }, "Fight with",
        h("select", { value: tree ?? "", onchange: (e) => { tree = e.target.value; } },
          choices.map((c) => h("option", { value: c.t.name }, `${c.t.name} · ${c.cost} points`))))
        : h("p", { class: "warn-text" }, "You need a finished tree within your budget. Make one in the Workshop."),
      h("button", { class: "primary big", disabled: busy || !tree, onclick: fight }, busy ? "Finding a battle…" : "Find a battle"),
      h("p", { class: "hint" }, "The map is generated for 2 to 4 teams. Opponents have trees of a similar cost and a similar rating. ",
        `Season battles give ${Math.round(p.modeXpFactor.season * 100)}% of your agents' XP, plus ${p.seasonPlayBonus} for taking part `,
        `and up to ${p.seasonPlaceBonus} more by place.`));
  }

  const boardCard = h("section", { class: "card" });
  function renderBoard() {
    const myBand = season.me?.band ?? Math.floor((me.level - 1) / 10);
    const rows = filter === "all" ? season.leaderboard : season.leaderboard.filter((r) => r.band === myBand);
    fill(boardCard,
      h("div", { class: "card-head" }, h("h2", {}, "Leaderboard"),
        h("div", { class: "tabs" },
          h("button", { class: `tab${filter === "all" ? " current" : ""}`, onclick: () => { filter = "all"; renderBoard(); } }, "Everyone"),
          h("button", { class: `tab${filter === "band" ? " current" : ""}`, onclick: () => { filter = "band"; renderBoard(); } },
            `Levels ${myBand * 10 + 1}-${myBand * 10 + 10}`))),
      leaderboardTable(rows, me),
      h("p", { class: "hint" }, "When the season ends, players are ranked against others in their band of 10 levels, so you compete with players near your level. ",
        "Rewards are a share of the XP your next level needs, the same share for the top of every band. ",
        `You need ${plural(3, "battle")} to be ranked.`));
  }

  async function startSeason() {
    try {
      await post("/api/season/start", {});
      location.reload();
    } catch (e) {
      showError(e.message);
    }
  }

  async function endSeason() {
    if (!confirm(`End ${season.name} now? Rewards are given out and the leaderboard is frozen.`)) return;
    try {
      await post(`/api/season/${season.id}/end`, {});
      location.hash = `#/season/${season.id}`;
    } catch (e) {
      showError(e.message);
    }
  }

  root.append(
    battleTabs("season"),
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, season ? season.name : "Season"),
        h("p", { class: "hint" }, season ? `Started ${formatDay(season.started)}. Ranked battles on generated maps.`
          : "Ranked battles on generated maps, with a leaderboard and rewards at the end.")),
      h("div", { class: "head-actions" },
        isAdmin() && season ? h("button", { class: "danger", onclick: endSeason }, "End season") : null,
        isAdmin() && !season ? h("button", { class: "primary", onclick: startSeason }, "Start a season") : null)));

  if (season) {
    renderFight();
    renderBoard();
    root.append(h("div", { class: "layout season-layout" }, boardCard, h("aside", { class: "side" }, fightCard)));
  } else {
    root.append(h("section", { class: "card" }, empty(isAdmin()
      ? "No season is running. Start one when players are ready."
      : "No season is running at the moment. In the meantime, try a Skirmish.")));
  }
  if (data.past.length) {
    root.append(h("section", { class: "card" }, h("h2", {}, "Past seasons"),
      h("ul", { class: "plain recent-list" }, data.past.map((s) => h("li", {},
        h("a", { href: `#/season/${s.id}` }, s.name),
        h("span", { class: "hint" }, ` ${formatDay(s.started)} to ${formatDay(s.ended)}`))))));
  }
}
