// Words and small pieces shared by the game screens: places, modes, levels.

import { h } from "./dom.js";

export const plural = (n, word, many = `${word}s`) => `${n} ${n === 1 ? word : many}`;

export function ordinal(n) {
  const tens = n % 100;
  const suffix = tens >= 11 && tens <= 13 ? "th" : { 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th";
  return `${n}${suffix}`;
}

export const MODES = {
  training: { label: "Training", hint: "Tutorials that teach one idea at a time." },
  skirmish: { label: "Skirmish", hint: "You pick the map and who to fight." },
  season: { label: "Season", hint: "Ranked battles on generated maps." },
  sandbox: { label: "Sandbox", hint: "Free practice with no rewards." },
};

export const modeBadge = (mode) => h("span", { class: `badge mode mode-${mode}` }, MODES[mode]?.label ?? mode);

// How a team did, in a few words: "Won", "2nd of 3", "Draw", "Lost". winners is the result's
// list of winning slots, which tells a draw from a win.
export function placeText(place, teams, winners = []) {
  if (place === null || place === undefined) return "";
  if (teams <= 1) return winners.length ? "Completed" : "Failed";
  if (place === 1) return winners.length > 1 ? "Draw" : "Won";
  if (place === teams) return teams === 2 ? "Lost" : `Last of ${teams}`;
  return `${ordinal(place)} of ${teams}`;
}

// Tabs at the top of the Battle screens.
export const battleTabs = (current) => h("nav", { class: "tabs big battle-tabs" },
  [["skirmish", "#/battle", "Skirmish"], ["season", "#/season", "Season"], ["sandbox", "#/sandbox", "Sandbox"]]
    .map(([key, href, label]) => h("a", { class: `tab${key === current ? " current" : ""}`, href }, label)));

// A level and XP bar: "Level 3", the XP into this level, and what the next one needs.
export function levelBar(me) {
  const span = me.nextLevelXp === null ? 1 : me.nextLevelXp - me.levelXp;
  const into = me.nextLevelXp === null ? 1 : me.xp - me.levelXp;
  return h("div", { class: "level" },
    h("div", { class: "level-head" },
      h("strong", {}, `Level ${me.level}`),
      h("span", { class: "hint" }, me.nextLevelXp === null ? `${me.xp} XP · top level`
        : `${me.xp} XP · ${me.nextLevelXp - me.xp} to level ${me.level + 1}`)),
    h("div", { class: "meter" }, h("span", { style: `width:${Math.max(2, Math.min(100, (100 * into) / span))}%` })));
}
