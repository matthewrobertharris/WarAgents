// A finished game's result (#/results/<id>): how each team placed, what you earned, and a way
// into the replay. Opening it marks it as seen in History.

import { get, post } from "../api.js";
import { teamColour } from "../colours.js";
import { formatDate, h } from "../dom.js";
import { modeBadge, ordinal, placeText, plural } from "../format.js";
import { loadUser, user } from "../session.js";

export async function mount(root, [gameId]) {
  const result = await get(`/api/results/${gameId}`);
  const me = user();
  const mine = result.placements.find((p) => p.player === me.id);
  const reward = result.rewards[me.id];
  const teams = result.placements.length;
  const verdict = mine ? placeText(mine.place, teams, result.winners) : "Finished";
  const won = mine && mine.place === 1;
  post(`/api/results/${gameId}/seen`).catch(() => {});

  const colour = (p) => p.colour ?? teamColour(result.placements.map((x) => ({ name: x.name, colour: x.colour })), p.name);
  const levelledUp = reward && reward.after.level > reward.before.level;
  if (levelledUp) loadUser();

  root.append(
    h("div", { class: "page-head" },
      h("div", {},
        h("p", { class: "eyebrow" }, modeBadge(result.mode), ` ${result.mapName ?? ""} · ${formatDate(result.created)}`),
        h("h1", { class: `verdict ${won ? "won" : mine ? "lost" : ""}` }, verdict),
        h("p", { class: "hint" }, `${result.outcome} · ${plural(result.turns, "turn")}`)),
      h("div", { class: "head-actions" },
        h("a", { class: "button", href: "#/history" }, "History"),
        result.mode === "skirmish" ? h("a", { class: "button", href: "#/battle" }, "Fight again") : null,
        result.mode === "season" ? h("a", { class: "button", href: "#/season" }, "Season") : null,
        h("a", { class: "button primary", href: `#/play/${gameId}` }, "Watch replay"))),

    h("div", { class: "layout results-layout" },
      h("section", { class: "card" },
        h("h2", {}, "Places"),
        h("table", { class: "places" },
          h("thead", {}, h("tr", {}, ["", "Team", "Agents left", "Agents in all", "Agent XP"].map((t) => h("th", {}, t)))),
          h("tbody", {}, result.placements.map((p) => h("tr", { class: p.player === me.id ? "me" : "" },
            h("td", { class: "place" }, ordinal(p.place)),
            h("td", {}, h("span", { class: "dot", style: `background:${colour(p)}` }), " ", p.name,
              p.player === me.id ? h("span", { class: "hint" }, " (you)") : null,
              p.eliminated ? h("span", { class: "hint" }, ` · out on turn ${p.eliminated}`) : null),
            h("td", { class: "num" }, p.alive),
            h("td", { class: "num" }, p.agents),
            h("td", { class: "num" }, p.exp)))))),

      h("aside", { class: "side" },
        reward ? h("section", { class: "card rewards" },
          h("h2", {}, "What you earned"),
          h("dl", { class: "stats" },
            h("dt", {}, "Your agents' XP"), h("dd", {}, reward.agentXp),
            h("dt", {}, "Account XP from them"), h("dd", {}, reward.fromAgents),
            reward.bonus ? [h("dt", {}, result.mode === "season" ? "Season bonus" : "Bonus"), h("dd", {}, reward.bonus)] : null,
            reward.rating ? [h("dt", {}, "Season rating"), h("dd", {},
              `${Math.round(reward.rating.before)} → ${Math.round(reward.rating.after)} `,
              h("span", { class: reward.rating.after >= reward.rating.before ? "good-text" : "warn-text" },
                `(${reward.rating.after >= reward.rating.before ? "+" : ""}${Math.round(reward.rating.after - reward.rating.before)})`))] : null,
            h("dt", {}, h("strong", {}, "Total")), h("dd", {}, h("strong", {}, `+${reward.total} XP`))),
          levelledUp
            ? h("p", { class: "level-up" }, `Level up! You're now level ${reward.after.level}, `,
              `and your trees can cost ${reward.after.budget} points (was ${reward.before.budget}).`)
            : h("p", { class: "hint" }, reward.after.nextLevelXp === null ? "You're at the top level."
              : `${reward.after.nextLevelXp - reward.after.xp} XP to level ${reward.after.level + 1}.`))
          : h("section", { class: "card" }, h("p", { class: "hint" }, "You didn't have a team in this game.")),
        h("section", { class: "card" },
          h("h2", {}, "Refine your tree"),
          h("p", { class: "hint" }, "Watch the replay to see what your agents did each turn and which branch of the tree they took. ",
            "Opponents' trees stay private, but you can see what their agents did."),
          h("a", { class: "button", href: "#/trees" }, "Open the Workshop")))));
}
