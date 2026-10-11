// The hub (#/): where you are (level, budget, default tree), what to do next, and results you
// haven't looked at yet.

import { get } from "../api.js";
import { formatDate, h } from "../dom.js";
import { levelBar, modeBadge, placeText } from "../format.js";
import { loadUser } from "../session.js";

const MENU = [
  ["#/training", "Training", "Short tutorials that teach one idea at a time, from your first move to building bases."],
  ["#/battle", "Battle", "Pick a map and who to fight, or take on practice bots. Battles earn XP."],
  ["#/trees", "Workshop", "Build and refine the decision trees your agents follow, within your points budget."],
  ["#/maps", "Maps", "Make your own maps, and publish them for other players to fight on."],
  ["#/history", "History", "Every game you've played, with results and full replays."],
  ["#/guide", "Guide", "Every input and action, what they cost, and how XP and levels work."],
];

// The one thing most worth doing next.
function nextStep(me, history, tutorials) {
  const next = tutorials?.find((t) => !t.completed);
  if (!history.length && next) {
    return ["Start with Training", `"${next.name}" shows you how to give your agents their first orders.`,
      `#/training/${next.id}`, "Start the first tutorial"];
  }
  if (!me.defaultTree.ready) {
    return ["Choose a default tree", "It defends you when other players pick you to fight. Until you have one, nobody can.",
      "#/trees", "Open the Workshop"];
  }
  if (next) {
    return ["Keep learning", `Next tutorial: "${next.name}".`, `#/training/${next.id}`, "Carry on training"];
  }
  return ["Pick a fight", "Take your tree into battle to earn XP, level up, and get a bigger budget.",
    "#/battle", "Go to Battle"];
}

export async function mount(root) {
  const [me, history, tutorials] = await Promise.all([
    loadUser(), get("/api/history"), get("/api/training").catch(() => null),
  ]);
  const unseen = history.filter((g) => g.finished && !g.seen);
  const [title, text, href, button] = nextStep(me, history, tutorials);
  const tree = me.defaultTree;

  root.append(
    h("section", { class: "hero hub-hero" },
      h("div", {},
        h("h1", {}, `Welcome back, ${me.name}`),
        h("p", { class: "lede" }, "Teach your agents to think, then send them to war.")),
      h("div", { class: "card hub-level" }, levelBar(me),
        h("p", { class: "hint" }, `Your trees can cost up to ${me.budget} points. Each level adds more.`))),

    h("section", { class: "card next-step" },
      h("div", {}, h("h2", {}, "Next"), h("p", { class: "next-title" }, title), h("p", { class: "hint" }, text)),
      h("a", { class: "button primary", href }, button)),

    h("div", { class: "hub-grid" },
      h("section", { class: "card" },
        h("div", { class: "card-head" }, h("h2", {}, "Default tree"), h("a", { href: "#/account" }, "Change")),
        tree.ready
          ? h("p", {}, h("strong", {}, tree.name), h("span", { class: "hint" }, ` · ${tree.cost} of ${tree.budget} points`))
          : h("p", { class: "warn-text" }, tree.name ? `${tree.name}: ${tree.problem}.` : "You haven't chosen one yet."),
        h("p", { class: "hint" }, "This tree plays for you when another player picks you to fight. ",
          tree.ready ? "" : "Until it's ready, nobody can.")),

      h("section", { class: "card" },
        h("div", { class: "card-head" }, h("h2", {}, unseen.length ? "New results" : "Recent games"),
          h("a", { href: "#/history" }, "All games")),
        (unseen.length ? unseen : history).length
          ? h("ul", { class: "plain recent-list" }, (unseen.length ? unseen : history).slice(0, 5).map((g) =>
            h("li", {},
              modeBadge(g.mode),
              h("a", { href: g.finished ? `#/results/${g.id}` : `#/play/${g.id}` }, g.name),
              h("span", { class: "hint" }, ` ${placeText(g.place, g.teamCount, g.winners)}${g.xp ? ` · +${g.xp} XP` : ""} · ${formatDate(g.created)}`),
              g.finished && !g.seen ? h("span", { class: "badge warn" }, "new") : null)))
          : h("p", { class: "empty" }, "No games yet."))),

    h("nav", { class: "menu" },
      MENU.map(([link, name, about]) =>
        h("a", { class: "menu-card", href: link },
          h("strong", {}, name, link === "#/history" && unseen.length ? h("span", { class: "badge warn" }, `${unseen.length} new`) : null),
          h("span", {}, about)))));
}
