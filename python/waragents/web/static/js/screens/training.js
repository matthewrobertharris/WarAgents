// Training: the tutorials by track (#/training), one tutorial (#/training/<id>), and watching a
// run of it (#/training/<id>/watch/<game id>). Nothing is locked; "recommended after" only
// suggests an order. Each tutorial has a tree of your own, tut-<id>, that you build in the
// Workshop and then run here.

import { get, post } from "../api.js";
import { mapPreview } from "../board.js";
import { empty, fill, h, showError } from "../dom.js";
import { plural } from "../format.js";
import { loadUser } from "../session.js";
import { fromJson, newUi, treeView } from "../treeview.js";
import { mountViewer } from "../viewer.js";

const LEVEL_CLASS = { Beginner: "ok", Intermediate: "", Advanced: "warn", Master: "warn" };

// ---- the tracks --------------------------------------------------------------------------

async function overview(root) {
  const tutorials = await get("/api/training");
  const done = tutorials.filter((t) => t.completed).length;
  const next = tutorials.find((t) => !t.completed);
  const tracks = [...new Set(tutorials.map((t) => t.track))];

  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Training"),
        h("p", { class: "hint" }, "Each tutorial teaches one idea on a small map. Do them in any order. ",
          "Completing one for the first time earns XP.")),
      h("div", { class: "head-actions" },
        h("span", { class: "hint" }, `${done} of ${tutorials.length} completed`),
        next ? h("a", { class: "button primary", href: `#/training/${next.id}` }, done ? "Next tutorial" : "Start") : null)),
    tutorials.length ? h("div", { class: "tracks" }, tracks.map((track) =>
      h("section", { class: "card track" },
        h("h2", {}, track),
        h("ol", { class: "plain tutorial-list" }, tutorials.filter((t) => t.track === track).map((t) =>
          h("li", {},
            h("a", { class: `tutorial-card${t.completed ? " done" : ""}${t === next ? " next" : ""}`, href: `#/training/${t.id}` },
              h("span", { class: "tick" }, t.completed ? "✓" : t.order),
              h("span", { class: "what" },
                h("strong", {}, t.name),
                h("span", { class: "hint" }, t.goal)),
              h("span", { class: `badge ${LEVEL_CLASS[t.level] ?? ""}` }, t.level)))))))) : empty("There are no tutorials yet."));
}

// ---- one tutorial ------------------------------------------------------------------------

function briefCard(t) {
  return h("section", { class: "card brief" },
    h("div", { class: "card-head" }, h("h2", {}, "Goal"), h("span", { class: "badge" }, t.level)),
    h("p", { class: "goal" }, t.goal),
    h("p", {}, t.brief),
    t.concepts.length ? h("p", { class: "concepts" }, "Uses: ",
      t.concepts.map((c) => h("a", { href: "#/guide", class: "concept" }, c))) : null,
    t.hints.length ? h("details", { class: "hints" }, h("summary", {}, plural(t.hints.length, "hint")),
      h("ol", {}, t.hints.map((hint) => h("li", {}, hint)))) : null);
}

async function page(root, tutorialId) {
  const t = await get(`/api/training/${tutorialId}`);
  const answerBox = h("div");
  let running = false;

  async function openTree() {
    try {
      const { treeId } = await post(`/api/training/${tutorialId}/tree`);
      location.hash = `#/trees/${treeId}?tutorial=${tutorialId}`;
    } catch (e) {
      showError(e.message);
    }
  }

  async function runIt() {
    if (running) return;
    running = true;
    try {
      if (!t.tree) await post(`/api/training/${tutorialId}/tree`);
      const done = await post(`/api/training/${tutorialId}/run`, {});
      location.hash = `#/training/${tutorialId}/watch/${done.gameId}`;
    } catch (e) {
      showError(e.problems?.length ? `Your tree isn't ready: ${e.problems.slice(0, 3).join("; ")}` : e.message);
    } finally {
      running = false;
    }
  }

  function showAnswer() {
    const trees = [t.solution, ...(t.solutionTrees ?? [])];
    fill(answerBox, trees.map((tree) => {
      const box = h("div", { class: "answer" });
      const ui = newUi();
      const view = fromJson(tree.root);
      const render = () => fill(box,
        trees.length > 1 ? h("h3", { class: "sub" }, tree.name) : null,
        treeView(view, ui, { defaultOpen: (node, depth) => depth < 3, onChange: render }));
      render();
      return box;
    }),
    h("p", { class: "hint" }, "There's more than one way to do it. Yours doesn't have to look like this."));
  }

  const treeState = !t.tree ? "You haven't started a tree for this one yet."
    : t.tree.finished ? `Your tree, ${t.tree.name}, is ready (${t.tree.cost} points).`
      : `Your tree, ${t.tree.name}, still has empty slots.`;

  root.append(
    h("div", { class: "page-head" },
      h("div", {},
        h("p", { class: "eyebrow" }, h("a", { href: "#/training" }, "Training"), ` · ${t.track} ${t.order}`),
        h("h1", {}, t.name, t.completed ? h("span", { class: "badge ok done-badge" }, `completed in ${plural(t.turns, "turn")}`) : null)),
      h("div", { class: "head-actions" },
        t.previous ? h("a", { class: "button", href: `#/training/${t.previous}` }, "Previous") : null,
        t.next ? h("a", { class: "button", href: `#/training/${t.next}` }, "Next") : null)),
    h("div", { class: "layout tutorial-layout" },
      h("div", { class: "side" },
        briefCard(t),
        h("section", { class: "card" },
          h("h2", {}, "Your tree"),
          h("p", {}, treeState),
          h("div", { class: "tutorial-actions" },
            h("button", { onclick: openTree }, t.tree ? "Edit my tree" : "Start my tree"),
            h("button", { class: "primary", onclick: runIt, disabled: !t.tree?.finished,
              title: t.tree?.finished ? "" : "Fill every slot in your tree first" }, "Run it")),
          h("p", { class: "hint" }, `The run stops after ${plural(t.maxTurns, "turn")}. `,
            t.completed ? "You've earned this one's XP already." : "Complete it for XP.")),
        h("section", { class: "card" },
          h("div", { class: "card-head" }, h("h2", {}, "Model answer"),
            h("button", { class: "small", onclick: showAnswer }, "Show it")),
          answerBox)),
      h("aside", { class: "side" },
        h("section", { class: "card" },
          h("h2", {}, "The map"),
          mapPreview({ ...t.map, width: t.map.dirt[0].length, height: t.map.dirt.length }, 320, 30),
          h("p", { class: "hint" }, "Your agent starts in the blue circle (slot 1). x runs left to right from 0, ",
            "and y runs bottom to top from 0."),
          t.bots.length ? h("p", { class: "hint" }, `Against: ${t.bots.map((b) => b.name).join(", ")}.`) : null))));
}

// ---- watching a run ----------------------------------------------------------------------

async function watch(root, tutorialId, gameId) {
  const [t, result] = await Promise.all([get(`/api/training/${tutorialId}`), get(`/api/results/${gameId}`)]);
  const passed = result.winners.includes(1);
  const reward = Object.values(result.rewards)[0];
  const outcome = h("div");
  const brief = h("div", { class: "side" }, briefCard(t), outcome);

  function showOutcome() {
    fill(outcome, h("section", { class: `card run-outcome ${passed ? "passed" : "failed"}` },
      h("h2", {}, passed ? "Tutorial complete!" : "Not this time"),
      h("p", {}, result.outcome),
      passed && reward?.total ? h("p", { class: "good-text" }, `+${reward.total} XP`) : null,
      passed && !reward?.total ? h("p", { class: "hint" }, "You'd already completed this one, so no XP this time.") : null,
      !passed ? h("p", { class: "hint" }, "Watch what your agent did, change your tree, and run it again.") : null,
      h("div", { class: "tutorial-actions" },
        h("a", { class: "button", href: `#/training/${tutorialId}` }, passed ? "Back to the tutorial" : "Try again"),
        passed && t.next ? h("a", { class: "button primary", href: `#/training/${t.next}` }, "Next tutorial") : null)));
    if (reward?.total) loadUser();
  }

  return mountViewer(root, gameId, {
    title: `Training: ${t.name}`,
    brief,
    endTurn: result.turns,
    actions: [
      h("button", { onclick: showOutcome }, "Skip to the result"),
      h("a", { class: "button", href: `#/training/${tutorialId}` }, "Tutorial"),
    ],
    onFinished: showOutcome,
  });
}

export async function mount(root, [tutorialId, gameId]) {
  if (tutorialId && gameId) return watch(root, tutorialId, gameId);
  if (tutorialId) return page(root, tutorialId);
  return overview(root);
}
