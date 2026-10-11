// Your account (#/account): name and colour, your default tree, your level, and your password.

import { get, put, reference } from "../api.js";
import { PALETTE } from "../colours.js";
import { teamCost, usableTrees } from "../cost.js";
import { fill, formatDay, h, showError } from "../dom.js";
import { levelBar, plural } from "../format.js";
import { loadUser, updateUser, user } from "../session.js";

export async function mount(root) {
  const [me, trees, history, ref] = await Promise.all([
    loadUser(), get("/api/catalogue/trees"), get("/api/history"), reference(),
  ]);
  const usable = usableTrees(trees, me.id);
  const battles = history.filter((g) => g.finished && g.teamCount > 1 && g.place);
  const wins = battles.filter((g) => g.place === 1).length;

  const note = h("span", { class: "hint save-status" });
  async function save(changes) {
    note.textContent = "Saving…";
    try {
      updateUser(await put("/api/me", changes));
      note.textContent = "Saved";
      renderTree();
      document.querySelector(".account-name")?.replaceChildren(
        h("span", { class: "dot", style: `background:${user().colour ?? ""}` }), user().name,
        h("span", { class: "badge level-badge" }, `Lv ${user().level}`));
    } catch (e) {
      note.textContent = "Not saved";
      showError(e.message);
      renderTree();
    }
  }

  const name = h("input", {
    value: me.name, autocomplete: "off",
    onchange: () => (name.value.trim() ? save({ name: name.value.trim() }) : showError("You need a name")),
  });
  const colour = h("input", { type: "color", value: me.colour ?? PALETTE[0], onchange: () => save({ colour: colour.value }) });
  const swatches = PALETTE.map((c) => h("button", {
    type: "button", class: "colour-swatch", title: c, style: `background:${c}`,
    onclick: () => { colour.value = c; save({ colour: c }); },
  }));

  const treeCard = h("section", { class: "card" });
  function renderTree() {
    const current = user();
    const status = current.defaultTree;
    const options = Object.values(usable).map((t) => {
      const cost = teamCost(t, usable, ref).cost;
      const problem = t.problems?.length ? "not finished" : cost > current.budget ? "over budget" : null;
      return { t, cost, problem };
    }).sort((a, b) => (b.t.owner === current.id) - (a.t.owner === current.id) || a.t.name.localeCompare(b.t.name));
    fill(treeCard,
      h("div", { class: "card-head" }, h("h2", {}, "Default tree"), note),
      h("p", { class: "hint" }, "This tree plays for you whenever another player picks you to fight, so pick your best. ",
        "It has to be finished and fit your budget."),
      h("select", {
        value: current.startTree ?? "",
        onchange: (e) => save({ startTree: e.target.value || null }),
      },
      h("option", { value: "" }, "None (nobody can pick you to fight)"),
      h("optgroup", { label: "Your trees" }, options.filter((o) => o.t.owner === current.id).map(option)),
      h("optgroup", { label: "Default trees" }, options.filter((o) => o.t.owner !== current.id).map(option))),
      status.ready
        ? h("p", { class: "good-text" }, `Ready: ${status.cost} of ${status.budget} points.`)
        : h("p", { class: "warn-text" }, status.name ? `${status.problem}.` : "Until you choose one, nobody can pick you to fight."));
  }
  const option = (o) => h("option", { value: o.t.name, disabled: Boolean(o.problem) },
    `${o.t.name} · ${o.cost} points${o.problem ? ` (${o.problem})` : ""}`);
  renderTree();

  const current = h("input", { type: "password", autocomplete: "current-password" });
  const fresh = h("input", { type: "password", autocomplete: "new-password", minLength: 8 });
  const again = h("input", { type: "password", autocomplete: "new-password" });
  const passwordNote = h("span", { class: "hint" });
  const passwordForm = h("form", {
    class: "fields",
    onsubmit: async (e) => {
      e.preventDefault();
      if (fresh.value !== again.value) return showError("The new passwords don't match");
      try {
        await put("/api/me/password", { current: current.value, new: fresh.value });
        passwordForm.reset();
        passwordNote.textContent = "Password changed";
      } catch (err) {
        showError(err.message);
      }
    },
  }, h("label", {}, "Current password", current), h("label", {}, "New password", fresh),
  h("label", {}, "New password again", again), h("div", {}, h("button", {}, "Change password"), " ", passwordNote));

  root.append(
    h("div", { class: "page-head" },
      h("div", { class: "player-head" },
        h("span", { class: "avatar big", style: `background:${me.colour ?? PALETTE[6]}` }, me.name.slice(0, 1).toUpperCase()),
        h("div", {}, h("h1", {}, me.name),
          h("p", { class: "hint" }, `Username ${me.id}`, me.created ? ` · joined ${formatDay(me.created)}` : "",
            me.admin ? " · admin" : ""))),
      h("div", { class: "head-actions" }, h("a", { class: "button", href: `#/players/${me.id}` }, "Your public profile"))),
    h("div", { class: "layout player-layout" },
      h("div", { class: "side" },
        h("section", { class: "card" },
          h("h2", {}, "Profile"),
          h("div", { class: "fields" },
            h("label", {}, "Name", name),
            h("p", { class: "hint" }, "How other players see you. You still sign in with your username."),
            h("label", {}, "Colour", h("span", { class: "colour-pick" }, colour, swatches)),
            h("p", { class: "hint" }, "Your teams play in this colour."))),
        treeCard,
        h("section", { class: "card" }, h("h2", {}, "Password"), passwordForm)),
      h("div", { class: "side" },
        h("section", { class: "card" }, h("h2", {}, "Level"), levelBar(me),
          h("p", { class: "hint" }, `Your trees can cost up to ${me.budget} points. `,
            h("a", { href: "#/guide" }, "How levels work"))),
        h("section", { class: "card" }, h("h2", {}, "Record"),
          h("dl", { class: "stats" },
            h("dt", {}, "Games"), h("dd", {}, history.length),
            h("dt", {}, "Battles"), h("dd", {}, battles.length),
            h("dt", {}, "Won"), h("dd", {}, battles.length ? `${wins} (${Math.round((100 * wins) / battles.length)}%)` : "0"),
            h("dt", {}, "Trees"), h("dd", {}, plural(trees.filter((t) => t.owner === me.id).length, "tree")))))));
}
