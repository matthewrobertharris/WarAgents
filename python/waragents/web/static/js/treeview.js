// A decision tree as a collapsible outline, so a big tree can be read a branch at a time.
//
// Nodes look like the server's: { id, kind, label, branches, children }. fromJson() converts a
// catalogue tree into that shape, adding each node's `path` (child indexes from the root) and
// `json` (the catalogue node, or null for an empty slot). The caller keeps a `ui` object between
// renders:
//   ui.open   Map of node key -> true/false for nodes the user opened or closed by hand
//   ui.focus  the key of the node shown as the top of the outline, or null for the whole tree
// Nodes the user hasn't touched follow defaultOpen(node, depth, onPath).
//
// The tree editor uses the same outline with its own rows. options.keyOf gives a node's key
// (its id by default), options.row(node) the elements after the branch label, and
// options.rowClass(node) extra classes for the row, and options.focusButton: false leaves out
// the built-in focus button. Each row has data-key set to its key.

import { h } from "./dom.js";

export const BRANCHES = {
  BOOLEAN: ["true", "false"],
  NUMERIC: ["<", "=", ">"],
  POSITION: ["left", "right", "up", "down", "current"],
};

export const newUi = () => ({ open: new Map(), focus: null });

export const pathKey = (path) => ["root", ...path].join(".");

function argText(arg) {
  if (arg === null || arg === undefined) return "…";
  if (typeof arg === "object") return `XY_VALUE ${arg.x} ${arg.y}`;
  return String(arg);
}

function callText(name, args) {
  return name ? [name, ...(args ?? []).map(argText)].join(" ") : "…";
}

// Numbers nodes in the same order as the server (depth first, parent before children), so a
// path from a running game lines up with a catalogue tree.
export function fromJson(root) {
  let next = 0;
  const convert = (node, path) => {
    const id = next++;
    if (!node) return { id, path, json: null, kind: "EMPTY", label: "empty slot", branches: [], children: [] };
    if (node.kind === "OUTPUT") {
      return { id, path, json: node, kind: "OUTPUT", label: callText(node.action, node.args), branches: [], children: [] };
    }
    const branches = BRANCHES[node.kind] ?? [];
    const label = (node.inputs ?? []).map((i) => (i ? callText(i.name, i.args) : "…")).join("  ·  ");
    const children = branches.map((_, i) => convert(node.children?.[i] ?? null, [...path, i]));
    return { id, path, json: node, kind: node.kind, label, branches, children };
  };
  return convert(root, []);
}

export function countNodes(node) {
  return 1 + node.children.reduce((sum, child) => sum + countNodes(child), 0);
}

const defaultRow = (node) => [
  h("span", { class: `kind ${node.kind}` }, node.kind === "OUTPUT" ? "DO" : node.kind === "EMPTY" ? "?" : node.kind),
  h("span", { class: "label" }, node.label),
];

export function treeView(root, ui, options = {}) {
  const {
    path = new Set(),
    defaultOpen = (node, depth, onPath) => onPath || depth < 2,
    onChange = () => {},
    keyOf = (node) => node.id,
    row = defaultRow,
    rowClass = () => "",
    focusButton = true,  // the editor puts focus in its own row menu instead
  } = options;

  const info = new Map();  // key -> { node, parent, branch, depth }
  (function index(node, parent, branch, depth) {
    info.set(keyOf(node), { node, parent, branch, depth });
    node.children.forEach((child, i) => index(child, node, node.branches[i], depth + 1));
  })(root, null, null, 0);

  const focus = info.get(ui.focus)?.node ?? root;
  const isOpen = (node, depth) => {
    const key = keyOf(node);
    return ui.open.has(key) ? ui.open.get(key) : defaultOpen(node, depth, path.has(node.id));
  };
  const setAll = (open) => {
    for (const key of info.keys()) ui.open.set(key, open);
    onChange();
  };

  const tools = h("div", { class: "tree-tools" },
    h("button", { class: "small", onclick: () => setAll(true) }, "Expand all"),
    h("button", { class: "small", onclick: () => setAll(false) }, "Collapse all"),
    path.size ? h("button", {
      class: "small", title: "Forget what you opened and closed, and follow the last decision",
      onclick: () => { ui.open.clear(); onChange(); },
    }, "Follow path") : null);

  // Breadcrumbs from the root to the focused branch.
  let crumbs = null;
  if (focus !== root) {
    const chain = [];
    for (let at = focus; at; at = info.get(keyOf(at)).parent) chain.unshift(at);
    crumbs = h("div", { class: "crumbs" },
      chain.map((node, i) => {
        const text = i === 0 ? "root" : info.get(keyOf(node)).branch;
        const crumb = node === focus
          ? h("span", { class: "crumb current" }, text)
          : h("button", { class: "crumb", onclick: () => { ui.focus = i === 0 ? null : keyOf(node); onChange(); } }, text);
        return [i ? h("span", { class: "sep" }, "›") : null, crumb];
      }),
      h("button", { class: "small", onclick: () => { ui.focus = null; onChange(); } }, "Whole tree"));
  }

  function renderNode(node, branch, depth) {
    const key = keyOf(node);
    const hasChildren = node.children.length > 0;
    const open = hasChildren && isOpen(node, depth);
    const extra = rowClass(node);
    const rowNode = h("div", {
      class: `node${path.has(node.id) ? " on-path" : ""}${extra ? ` ${extra}` : ""}`,
      "data-key": String(key),
    },
    hasChildren
      ? h("button", {
        class: "caret", title: open ? "Collapse" : "Expand", "aria-expanded": String(open),
        onclick: () => { ui.open.set(key, !open); onChange(); },
      }, open ? "▾" : "▸")
      : h("span", { class: "caret" }),
    branch !== null ? h("span", { class: "branch" }, branch) : null,
    row(node),
    hasChildren && !open ? h("span", { class: "count" }, `${countNodes(node) - 1} below`) : null,
    focusButton && hasChildren && node !== focus
      ? h("button", {
        class: "focus", title: "Show just this branch",
        onclick: () => { ui.focus = key; ui.open.set(key, true); onChange(); },
      }, "focus")
      : null);
    const li = h("li", {}, rowNode);
    if (open) {
      li.append(h("ul", {}, node.children.map((child, i) => renderNode(child, node.branches[i], depth + 1))));
    }
    return li;
  }

  const focusInfo = info.get(keyOf(focus));
  const outline = h("ul", { class: "outline" },
    renderNode(focus, focus === root ? null : focusInfo.branch, focusInfo.depth));
  return h("div", { class: "tree-view" }, tools, crumbs, h("div", { class: "tree" }, outline));
}
