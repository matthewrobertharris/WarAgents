// The guide (#/guide): how the game works, then what agents can do (the DO actions), then the
// questions they can ask, then the ways to play, XP and levels, and what trees cost. The actions,
// questions and numbers come from /api/reference, so they always match the server.

import { reference } from "../api.js";
import { h } from "../dom.js";

const KIND_TEXT = {
  boolean: ["Yes/no questions", "BOOLEAN", "Asked by BOOLEAN nodes, which have two branches: true and false."],
  numeric: ["Number questions", "NUMERIC", "Asked in pairs by NUMERIC nodes, which compare the first number with the second and have three branches: <, = and >. Use VALUE for a fixed number, such as “is my health < 50?”."],
  position: ["Which-way questions", "POSITION", "Asked by POSITION nodes, which have five branches: left, right, up, down, and current (it's right here, or there's nowhere to go)."],
};

const ARG_TEXT = { position: "a position", int: "a number", activity: "an action", name: "a tree name" };

// What each position argument points at. Anything the server adds later still gets listed.
const POSITION_TEXT = {
  CURRENT: "The tile the agent is standing on.",
  LEFT: "The tile next to it on the left.",
  RIGHT: "The tile next to it on the right.",
  UP: "The tile above it (up the screen).",
  DOWN: "The tile below it.",
  PREVIOUS: "The tile it was on before its last move. Confuses an agent that hasn't moved yet.",
  PRIMARY: "A tile it remembered with SET_PRIMARY. Confuses an agent that hasn't remembered one.",
  SECONDARY: "A tile it remembered with SET_SECONDARY. Confuses an agent that hasn't remembered one.",
  "XY_VALUE x y": "A fixed tile on the map, by its x and y (y = 0 is the bottom row).",
};

// The DO actions in groups, in the order a new player needs them. Directional actions are one row.
const ACTION_GROUPS = [
  ["Moving", ["MOVE_"]],
  ["Fighting", ["ATTACK_", "DEFEND"]],
  ["Food", ["EAT", "LIFT_FOOD", "DROP_FOOD"]],
  ["Dirt (changing the ground)", ["LIFT_DIRT", "DROP_DIRT"]],
  ["Growing the team", ["REPRODUCE"]],
  ["Memory and other trees", ["SET_PRIMARY", "CLEAR_PRIMARY", "SET_SECONDARY", "CLEAR_SECONDARY", "CHANGE_TREE"]],
];
const SYSTEM_ACTIONS = ["CONFUSED", "DEATH"];
const DIRECTIONS = ["LEFT", "RIGHT", "UP", "DOWN"];

const table = (headings, rows, kind = "") => h("div", { class: "table-wrap" }, h("table", { class: `guide-table ${kind}` },
  h("thead", {}, h("tr", {}, headings.map((t) => h("th", {}, t)))),
  h("tbody", {}, rows)));

// The actions as rows: [name shown, the action it stands for, its description].
function actionRows(actions, prefixes) {
  const rows = [];
  for (const prefix of prefixes) {
    if (prefix.endsWith("_")) {
      const family = DIRECTIONS.map((d) => actions.find((a) => a.name === `${prefix}${d}`)).filter(Boolean);
      if (!family.length) continue;
      const doc = family[0].doc.replace(/\bleft\b/, "in that direction");
      rows.push([family.map((a, i) => (i ? `_${a.name.slice(prefix.length)}` : a.name)).join(" "), family[0], doc]);
    } else {
      const action = actions.find((a) => a.name === prefix);
      if (action) rows.push([action.name, action, action.doc]);
    }
  }
  return rows;
}

export async function mount(root) {
  const ref = await reference();
  const p = ref.progression;
  const pct = (n) => `${Math.round(n * 100)}%`;
  const sections = [];
  const section = (id, title, ...body) => {
    sections.push([id, title]);
    return h("section", { class: "card guide-section", id: `guide-${id}` }, h("h2", {}, title), ...body);
  };

  // Every action is in a group, so one the server adds later still shows up, under "Other".
  const grouped = new Set(ACTION_GROUPS.flatMap(([, names]) => names.flatMap((n) => (n.endsWith("_")
    ? DIRECTIONS.map((d) => `${n}${d}`) : [n]))));
  const others = ref.actions.filter((a) => !grouped.has(a.name) && !SYSTEM_ACTIONS.includes(a.name)).map((a) => a.name);
  const groups = [...ACTION_GROUPS, ...(others.length ? [["Other", others]] : [])];
  const confused = ref.actions.find((a) => a.name === "CONFUSED");

  const content = [
    section("basics", "How it works",
      h("p", {}, "You don't control your agents during a game. Before it starts, you give your team a ",
        h("strong", {}, "decision tree"), ", and every turn each agent works through it from the top."),
      h("p", {}, "A tree is made of ", h("strong", {}, "questions"), " and ", h("strong", {}, "actions"), ". ",
        "Each question looks at the world from the agent's point of view, and its answer picks which branch to follow. ",
        "The agent keeps answering questions down the tree until it reaches an action, does it, and its turn is over."),
      h("ul", {},
        h("li", {}, h("strong", {}, "DO"), " nodes are the actions at the ends of the branches: move, attack, eat, and so on. ",
          "They're listed in the next section."),
        h("li", {}, h("strong", {}, "BOOLEAN"), " nodes ask a yes/no question, such as “is there food here?”"),
        h("li", {}, h("strong", {}, "NUMERIC"), " nodes compare two numbers, such as “is my health less than 50?”"),
        h("li", {}, h("strong", {}, "POSITION"), " nodes ask which way something is, such as “which way is the nearest enemy?”")),
      h("p", {}, h("strong", {}, "A tree is only as good as your understanding of its questions. "),
        "Each one asks something precise, and the answer means exactly that and nothing more. ",
        h("code", {}, "LEGAL_MOVE"), " says whether any neighbouring tile is on the map and empty, not which one, and doesn't look at heights, ",
        "so a move can still fail after it says yes. ", h("code", {}, "HAS_FOOD CURRENT"), " is about the tile the agent is on, ",
        "not the tiles around it. ", h("code", {}, "ENEMY_ADJACENT_POS"), " answers “current” when there's no enemy next to the agent. ",
        "Read what a question means before you build on it."),
      h("p", {}, "If a question can't be answered at all (asking about PRIMARY before the agent has remembered one, say), the agent is ",
        h("strong", {}, "Confused"), confused ? ` and loses health (${confused.doc.match(/loses (\d+)/)?.[1] ?? "some"}). ` : ". ",
        "Guard risky questions with VALID_POSITION or IN_BOUNDS first."),
      h("p", {}, "The board: every tile has a height (dirt) and some food. Agents lose health climbing and carrying, and get it back by eating. ",
        "Heights differing by 3 or more can't be crossed. Plants grow food on and around their tile every turn.")),

    section("actions", "What agents can do",
      h("p", {}, "Every branch of a tree ends in a ", h("strong", {}, "DO"), " node: one of these actions. ",
        "An agent does exactly one action a turn. Many need something to be true first, such as food to eat or an empty tile to move to. ",
        "If it isn't, the action fails and the turn is wasted, which is what the questions in your tree are for: ",
        "picking an action that will work, at the right time."),
      ...groups.flatMap(([title, names]) => [
        h("h3", { class: "sub" }, title),
        table(["Action", "Takes", "What it does", "Cost", "Agent XP"], actionRows(ref.actions, names).map(([name, a, doc]) =>
          h("tr", {}, h("td", {}, h("code", {}, name)),
            h("td", { class: "hint" }, a.args.map((arg) => ARG_TEXT[arg] ?? arg).join(", ")),
            h("td", {}, doc), h("td", { class: "num" }, a.cost), h("td", { class: "num" }, a.exp || ""))), "actions"),
      ]),
      confused ? h("p", { class: "hint" }, h("strong", {}, "CONFUSED"), " isn't something you choose. It's what happens instead of ",
        "an action when an agent's tree asks a question that can't be answered: ",
        confused.doc.replace(/^.*?: /, "")) : null),

    section("questions", "The questions",
      h("p", {}, "Decision nodes ask about the world from the agent's point of view: its own tile, the tiles next to it, ",
        "places it remembers, its team and itself. The answer picks the branch. ",
        "Most questions take a ", h("strong", {}, "position"), ", which says which tile they're about:"),
      table(["Position", "Which tile"], ref.positions.map((name) =>
        h("tr", {}, h("td", {}, h("code", {}, name)), h("td", {}, POSITION_TEXT[name] ?? ""))), "positions"),
      ...Object.entries(KIND_TEXT).flatMap(([kind, [title, node, about]]) => [
        h("h3", { class: "sub" }, `${title} (${node} nodes)`),
        h("p", { class: "hint" }, about),
        table(["Question", "Takes", "What it asks", "Cost"], ref.inputs.filter((i) => i.kind === kind).map((i) =>
          h("tr", {}, h("td", {}, h("code", {}, i.name)),
            h("td", { class: "hint" }, i.args.map((a) => ARG_TEXT[a] ?? a).join(", ")),
            h("td", {}, i.doc), h("td", { class: "num" }, i.cost))), "questions"),
      ])),

    section("modes", "Ways to play",
      h("dl", { class: "guide-modes" },
        h("dt", {}, "Training"), h("dd", {}, "Short tutorials, each teaching one idea on a small map. Nothing is locked: do them in any order. ",
          "The first time you complete one you earn its agents' XP plus a bonus."),
        h("dt", {}, "Skirmish"), h("dd", {}, "You pick the map, your tree and who to fight: other players (who play their default tree) or practice bots."),
        h("dt", {}, "Season"), h("dd", {}, "Ranked battles on maps the server generates, against players near your rating. Seasons have a leaderboard and rewards."),
        h("dt", {}, "History"), h("dd", {}, "Every game you've been in. Each one replays exactly, turn by turn, from its seed and starting setup."),
        h("dt", {}, "Analytics"), h("dd", {}, "Charts of how your trees have done and what your opponents did, filtered any way you like, ",
          "with an export of every turn to analyse yourself."),
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
      h("p", {}, "Every node costs points. A decision costs what its questions cost, and each action costs what its table above says. ",
        "A tree that switches to other trees with CHANGE_TREE pays for them too, once each."),
      h("p", {}, "To go into battle, a tree has to fit your budget, which grows with your level. ",
        "The Workshop shows each tree's cost against your budget as you build it, and each question's cost is next to its name in the dropdowns.")),
  ];

  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Guide"),
      h("p", { class: "hint" }, "How the game works, everything your agents can do and ask, and how you level up."))),
    h("nav", { class: "tabs big guide-contents" }, sections.map(([id, title]) =>
      h("button", { class: "tab", onclick: () => root.querySelector(`#guide-${id}`).scrollIntoView({ behavior: "smooth" }) }, title))),
    ...content);
}
