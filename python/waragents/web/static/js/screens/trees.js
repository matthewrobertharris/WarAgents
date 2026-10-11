// Decision trees: your trees and the default trees (#/trees), and the editor for one tree
// (#/trees/<id>, in treeeditor.js). Admins see every player's trees and can change the defaults.

import { get, post, remove } from "../api.js";
import { empty, h, showError } from "../dom.js";
import { isAdmin, user } from "../session.js";
import { countNodes, fromJson } from "../treeview.js";
import * as editor from "./treeeditor.js";

export function status(tree) {
  const n = tree.problems?.length ?? 0;
  return n ? h("span", { class: "badge warn", title: tree.problems.map((p) => `${p.where}: ${p.message}`).join("\n") },
    `${n} to fix`) : h("span", { class: "badge ok" }, "ready");
}

function switchesTo(tree) {
  const names = new Set();
  (function walk(node) {
    if (!node) return;
    if (node.action === "CHANGE_TREE" && node.args?.[0]) names.add(node.args[0]);
    (node.children ?? []).forEach(walk);
  })(tree.root);
  return [...names];
}

// A name no other tree of this owner has: base, base-2, base-3, ...
export function freeName(trees, owner, base) {
  const taken = new Set(trees.filter((t) => t.owner === owner).map((t) => t.name));
  let name = base;
  for (let n = 2; taken.has(name); n++) name = `${base}-${n}`;
  return name;
}

async function list(root) {
  const [trees, players] = await Promise.all([get("/api/catalogue/trees"), get("/api/catalogue/players")]);
  const me = user();

  async function create(owner = null) {
    try {
      const made = await post("/api/catalogue/trees", { name: freeName(trees, owner, "new-tree"), owner, root: null });
      location.hash = `#/trees/${made.id}?new=1`;
    } catch (e) {
      showError(e.message);
    }
  }

  async function duplicate(tree) {
    try {
      const { id, problems, ...data } = tree;
      // A player's copy of a default tree is theirs, so it can keep the name.
      const owner = isAdmin() ? tree.owner : user().id;
      const base = owner === tree.owner ? `${tree.name}-copy` : tree.name;
      const made = await post("/api/catalogue/trees", { ...data, owner, name: freeName(trees, owner, base) });
      location.hash = `#/trees/${made.id}?new=1`;
    } catch (e) {
      showError(e.message);
    }
  }

  async function del(tree) {
    const users = trees.filter((t) => t !== tree && switchesTo(t).includes(tree.name)).map((t) => t.name);
    const warning = users.length ? ` ${users.join(", ")} switch${users.length === 1 ? "es" : ""} to it by name.` : "";
    if (!confirm(`Delete the tree "${tree.name}"?${warning} Saved games keep their own copy.`)) return;
    try {
      await remove(`/api/catalogue/trees/${tree.id}`);
      root.replaceChildren();
      await list(root);
    } catch (e) {
      showError(e.message);
    }
  }

  root.append(h("div", { class: "page-head" },
    h("div", {},
      h("h1", {}, "Decision trees"),
      h("p", { class: "hint" },
        "Your trees are yours alone: nobody else can see them. Default trees can be used by everyone. ",
        "CHANGE_TREE looks in your own trees first, then the defaults.")),
    h("div", { class: "head-actions" }, h("button", { class: "primary", onclick: () => create(me.id) }, "New tree"))));

  const groups = [[me.id, "Your trees", trees.filter((t) => t.owner === me.id)]];
  if (isAdmin()) {
    groups.push(...players.filter((p) => p.id !== me.id)
      .map((p) => [p.id, `${p.name}'s trees`, trees.filter((t) => t.owner === p.id)])
      .filter(([, , group]) => group.length));
    const orphans = trees.filter((t) => t.owner !== null && !players.some((p) => p.id === t.owner));
    if (orphans.length) groups.push([undefined, "Trees whose owner is missing", orphans]);
  }
  groups.push([null, "Default trees", trees.filter((t) => t.owner === null)]);

  for (const [owner, title, group] of groups) {
    const editable = isAdmin() || owner === me.id;
    root.append(h("section", { class: "card" },
      h("div", { class: "card-head" }, h("h2", {}, title),
        owner !== undefined && editable ? h("button", { class: "small", onclick: () => create(owner) }, "New tree here") : null),
      owner === null && !isAdmin() ? h("p", { class: "hint" },
        "Duplicate a default tree to make your own copy you can change.") : null,
      group.length ? h("ul", { class: "tree-list" }, group.map((tree) => h("li", {},
        h("a", { href: `#/trees/${tree.id}` }, h("strong", {}, tree.name)),
        h("span", { class: "hint" }, `${tree.root ? countNodes(fromJson(tree.root)) : 0} nodes · ${tree.cost} points`),
        tree.owner === me.id && tree.name === me.startTree ? h("span", { class: "badge ok" }, "default") : null,
        switchesTo(tree).length ? h("span", { class: "hint" }, `switches to ${switchesTo(tree).join(", ")}`) : null,
        status(tree),
        h("span", { class: "row-actions" },
          h("a", { class: "button small", href: `#/trees/${tree.id}` }, editable ? "Edit" : "View"),
          h("button", { class: "small", onclick: () => duplicate(tree) }, "Duplicate"),
          editable ? h("button", { class: "small danger", onclick: () => del(tree) }, "Delete") : null))))
        : empty(owner === me.id ? "None yet. Start a new tree, or duplicate a default one." : "None yet.")));
  }
}

export async function mount(root, [treeId], query) {
  if (treeId) return editor.mount(root, treeId, query);
  return list(root);
}
