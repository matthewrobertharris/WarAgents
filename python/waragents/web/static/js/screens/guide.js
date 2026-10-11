// The guide (#/guide): how the game works, how XP, levels and the points budget work, and every
// input and action with what it costs. The numbers come from /api/reference, so they always
// match the server.

import { reference } from "../api.js";
import { h } from "../dom.js";

const KIND_TEXT = {
  boolean: ["Yes/no inputs", "Used by BOOLEAN nodes, which branch on true or false."],
  numeric: ["Number inputs", "Used in pairs by NUMERIC nodes, which branch on whether the first is less than, equal to or more than the second."],
  position: ["Position inputs", "Used by POSITION nodes, which branch on which way the position is from the agent: left, right, up, down, or right here."],
};

const ARG_TEXT = { position: "a position", int: "a number", activity: "an action", name: "a tree name" };

const table = (headings, rows) => h("div", { class: "table-wrap" }, h("table", { class: "guide-table" },
  h("thead", {}, h("tr", {}, headings.map((t) => h("th", {}, t)))),
  h("tbody", {}, rows)));

export async function mount(root) {
  const ref = await reference();
  const p = ref.progression;
  const pct = (n) => `${Math.round(n * 100)}%`;
  const sections = [];
  const section = (id, title, ...body) => {
    sections.push([id, title]);
    return h("section", { class: "card guide-section", id: `guide-${id}` }, h("h2", {}, title), ...body);
  };

  const content = [
    section("basics", "How it works",
      h("p", {}, "You don't control your agents during a game. You give them a decision tree, and every turn each agent ",
        "walks its tree from the top: each question it answers picks a branch, until it reaches an action, which it does."),
      h("ul", {},
        h("li", {}, h("strong", {}, "DO"), " nodes are actions: move, attack, eat, lift and drop dirt or food, reproduce, and so on."),
        h("li", {}, h("strong", {}, "BOOLEAN"), " nodes ask a yes/no question, such as “is there food here?”"),
        h("li", {}, h("strong", {}, "NUMERIC"), " nodes compare two numbers, such as “is my health less than 50?”"),
        h("li", {}, h("strong", {}, "POSITION"), " nodes ask which way something is, such as “which way is my primary position?”")),
      h("p", {}, "If a question can't be answered (asking about PRIMARY before setting it, say), the agent is ",
        h("strong", {}, "Confused"), " and hurts itself. Guard risky questions with VALID_POSITION or IN_BOUNDS first."),
      h("p", {}, "Positions you can ask about: ", h("code", {}, ref.positions.join(", ")),
        ". PRIMARY and SECONDARY are positions the agent remembers with SET_PRIMARY and SET_SECONDARY."),
      h("p", {}, "Agents lose health climbing and carrying, and get it back by eating. Heights differing by 3 or more can't be crossed. ",
        "Plants grow food on and around their tile every turn.")),

    section("modes", "Ways to play",
      h("dl", { class: "guide-modes" },
        h("dt", {}, "Training"), h("dd", {}, "Short tutorials, each teaching one idea on a small map. Nothing is locked: do them in any order. ",
          "The first time you complete one you earn its agents' XP plus a bonus."),
        h("dt", {}, "Skirmish"), h("dd", {}, "You pick the map, your tree and who to fight: other players (who play their default tree) or practice bots."),
        h("dt", {}, "Season"), h("dd", {}, "Ranked battles on maps the server generates, against players near your rating. Seasons have a leaderboard and rewards."),
        h("dt", {}, "History"), h("dd", {}, "Every game you've been in. Each one replays exactly, turn by turn, from its seed and starting setup."),
        h("dt", {}, "Sandbox"), h("dd", {}, "Set up any game and watch it play out. Good for testing trees. No XP.")),
      h("p", {}, "Battles are decided the moment they start. You see the result first, and can watch the replay whenever you like. ",
        "Other players' trees stay private: you see what their agents did, not why."),
      h("p", {}, "Your ", h("strong", {}, "default tree"), " (set on your Account) plays for you when someone else picks you to fight. ",
        "Until you have one that's finished and within budget, nobody can pick you.")),

    section("xp", "XP and levels",
      h("p", {}, "Every game gives XP to individual agents for what they do. When the game ends, your agents' XP turns into ",
        h("strong", {}, "account XP"), ", which raises your level. A higher level means a bigger points budget for your trees."),
      table(["Action", "Agent XP"], [
        ...ref.actions.filter((a) => a.exp > 0 && !/_(RIGHT|UP|DOWN)$/.test(a.name)).map((a) =>
          h("tr", {}, h("td", {}, a.name.replace(/_LEFT$/, "_*")), h("td", { class: "num" }, a.exp))),
        h("tr", {}, h("td", {}, "A kill (on top of the attack)"), h("td", { class: "num" }, p.killExp)),
        h("tr", {}, h("td", {}, "Defending against an attack"), h("td", { class: "num" }, p.blockExp)),
      ]),
      h("p", { class: "hint" }, "Failed actions earn nothing."),
      table(["Mode", "Account XP from your agents' XP", "Bonus"], [
        h("tr", {}, h("td", {}, "Training"), h("td", {}, pct(p.modeXpFactor.training), ", the first time you complete a tutorial"),
          h("td", {}, Object.entries(p.tutorialBonus).map(([level, xp]) => `${level} ${xp}`).join(" · "))),
        h("tr", {}, h("td", {}, "Skirmish"), h("td", {}, pct(p.modeXpFactor.skirmish)), h("td", {}, "none")),
        h("tr", {}, h("td", {}, "Season"), h("td", {}, pct(p.modeXpFactor.season)),
          h("td", {}, `${p.seasonPlayBonus} for playing, plus up to ${p.seasonPlaceBonus} by place`)),
      ]),
      table(["Level", "Total account XP", "Points budget"], p.levels.map((l) =>
        h("tr", {}, h("td", {}, l.level), h("td", { class: "num" }, l.xp), h("td", { class: "num" }, l.budget))))),

    section("cost", "What trees cost",
      h("p", {}, "Every node costs points. A decision costs what its inputs cost, and each action costs 1. ",
        "A tree that switches to other trees with CHANGE_TREE pays for them too, once each."),
      h("p", {}, "To go into battle, a tree has to fit your budget. The Workshop shows each tree's cost against your budget as you build it, ",
        "and each input's cost is next to its name in the dropdowns."),
      ...Object.entries(KIND_TEXT).flatMap(([kind, [title, about]]) => [
        h("h3", { class: "sub" }, title),
        h("p", { class: "hint" }, about),
        table(["Input", "Takes", "Cost", "What it tells you"], ref.inputs.filter((i) => i.kind === kind).map((i) =>
          h("tr", {}, h("td", {}, h("code", {}, i.name)),
            h("td", { class: "hint" }, i.args.map((a) => ARG_TEXT[a] ?? a).join(", ")),
            h("td", { class: "num" }, i.cost), h("td", {}, i.doc)))),
      ]),
      h("h3", { class: "sub" }, "Actions"),
      table(["Action", "Cost", "Agent XP", "What it does"], ref.actions.filter((a) => a.name !== "DEATH").map((a) =>
        h("tr", {}, h("td", {}, h("code", {}, a.name)), h("td", { class: "num" }, a.cost),
          h("td", { class: "num" }, a.exp || ""), h("td", {}, a.doc))))),
  ];

  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Guide"),
      h("p", { class: "hint" }, "Everything your agents can sense and do, and how you level up."))),
    h("nav", { class: "tabs big guide-contents" }, sections.map(([id, title]) =>
      h("button", { class: "tab", onclick: () => root.querySelector(`#guide-${id}`).scrollIntoView({ behavior: "smooth" }) }, title))),
    ...content);
}
