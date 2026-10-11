// Editing one decision tree (#/trees/<id>). The tree is the collapsible outline from
// treeview.js with a dropdown for every choice on each row:
//   - every row has a node type: an empty slot, DO (an action), BOOLEAN, NUMERIC or POSITION
//   - a DO row picks an action, plus its argument (CHANGE_TREE's tree, SET_PRIMARY's position)
//   - a BOOLEAN row picks a boolean input and has true/false branches
//   - a NUMERIC row picks two numeric inputs and branches on how the first compares to the second
//   - a POSITION row picks a position input and branches on which way that position is
//   - an input's arguments are a position, a whole number, an action or a tree name
// Only what fits a slot is offered, but nothing is held back yet (by level or points, say).
// Changes save themselves, and Ctrl+Z / Ctrl+Y undo and redo.

import { get, put, reference } from "../api.js";
import { fill, h, showError } from "../dom.js";
import { countNodes, fromJson, newUi, pathKey, treeView } from "../treeview.js";

const KINDS = [
  ["OUTPUT", "DO", "Do an action. A leaf of the tree."],
  ["BOOLEAN", "BOOLEAN", "Ask a yes/no question, then go down the true or false branch."],
  ["NUMERIC", "NUMERIC", "Compare two numbers, then go down the <, = or > branch."],
  ["POSITION", "POSITION", "Work out which way a position is, then go down that direction's branch."],
];

// Actions grouped for the dropdown.
const ACTION_GROUPS = [
  ["Move", ["MOVE_LEFT", "MOVE_RIGHT", "MOVE_UP", "MOVE_DOWN"]],
  ["Attack", ["ATTACK_LEFT", "ATTACK_RIGHT", "ATTACK_UP", "ATTACK_DOWN"]],
  ["Stay", ["DEFEND", "EAT", "REPRODUCE"]],
  ["Carry", ["LIFT_FOOD", "DROP_FOOD", "LIFT_DIRT", "DROP_DIRT"]],
  ["Remember a position", ["SET_PRIMARY", "CLEAR_PRIMARY", "SET_SECONDARY", "CLEAR_SECONDARY"]],
  ["Trees", ["CHANGE_TREE"]],
  ["System", ["CONFUSED", "DEATH"]],
];

// Some clipboard that outlives one visit to the editor, so a branch can be copied between trees.
let clipboard = null;

export async function mount(root, treeId, query) {
  const [saved, ref, trees, players] = await Promise.all([
    get(`/api/catalogue/trees/${treeId}`), reference(), get("/api/catalogue/trees"), get("/api/catalogue/players"),
  ]);
  const { id, problems = [], ...tree } = saved;
  const inputs = Object.fromEntries(ref.inputs.map((i) => [i.name, i]));
  const actions = Object.fromEntries(ref.actions.map((a) => [a.name, a]));
  const positions = ref.positions.filter((p) => !p.startsWith("XY_VALUE"));

  const ed = {
    tree,
    problems,
    ui: newUi(),
    history: [],
    future: [],
    lastLabel: null,
    lastAt: 0,
    dirty: false,
    saving: false,
    saveAgain: false,
    saveTimer: null,
  };

  // ---- layout ----------------------------------------------------------------------

  const title = h("h1", {}, tree.name);
  const statusText = h("span", { class: "save-status" }, "Saved");
  const undoButton = h("button", { class: "small", title: "Ctrl+Z", onclick: undo }, "Undo");
  const redoButton = h("button", { class: "small", title: "Ctrl+Y", onclick: redo }, "Redo");
  const outline = h("div", { class: "tree-editor" });
  const details = h("section", { class: "card" });
  const problemsCard = h("section", { class: "card" });
  const clipText = h("span", { class: "hint" });
  root.append(
    h("div", { class: "page-head" },
      h("div", {}, title, h("p", { class: "hint" }, "Changes save automatically. ", statusText)),
      h("div", { class: "head-actions" }, h("a", { class: "button", href: "#/trees" }, "All trees"))),
    h("div", { class: "layout tree-layout" },
      h("section", { class: "card" },
        h("div", { class: "controls" }, undoButton, redoButton, clipText,
          h("span", { class: "hint status" }, "Each row's ⋯ menu has focus, copy, paste and clear.")),
        outline),
      h("aside", { class: "side" }, details, problemsCard)));

  // ---- the tree as data --------------------------------------------------------------

  function getAt(path) {
    let node = ed.tree.root;
    for (const i of path) node = node.children[i];
    return node;
  }

  function setAt(path, value) {
    if (!path.length) ed.tree.root = value;
    else getAt(path.slice(0, -1)).children[path.at(-1)] = value;
  }

  const availableTrees = () => {
    const own = trees.filter((t) => t.owner === ed.tree.owner && ed.tree.owner !== null).map((t) => t.name);
    const defaults = trees.filter((t) => t.owner === null).map((t) => t.name);
    return [...new Set([...own, ...defaults, ed.tree.name])].sort();
  };

  function defaultArg(kind) {
    switch (kind) {
      case "position": return "CURRENT";
      case "int": return 50;
      case "activity": return "MOVE_LEFT";
      default: return ed.tree.name;
    }
  }

  const withArgs = (data, spec) => (spec.length ? { ...data, args: spec.map(defaultArg) } : data);

  // ---- changes, undo and saving (as in the map editor) -------------------------------

  const snapshot = () => JSON.stringify(ed.tree);

  function change(label, fn, { coalesce = false, refresh = "all" } = {}) {
    const now = performance.now();
    if (!coalesce || label !== ed.lastLabel || now - ed.lastAt > 800) {
      ed.history.push(snapshot());
      if (ed.history.length > 200) ed.history.shift();
    }
    ed.future = [];
    ed.lastLabel = label;
    ed.lastAt = now;
    fn();
    scheduleSave();
    if (refresh === "all") render();
  }

  function restore(text) {
    ed.tree = JSON.parse(text);
    ed.lastLabel = null;
    scheduleSave();
    render();
  }

  function undo() {
    if (!ed.history.length) return;
    ed.future.push(snapshot());
    restore(ed.history.pop());
  }

  function redo() {
    if (!ed.future.length) return;
    ed.history.push(snapshot());
    restore(ed.future.pop());
  }

  function setStatus(text, bad = false) {
    statusText.textContent = text;
    statusText.classList.toggle("error-text", bad);
  }

  function scheduleSave() {
    ed.dirty = true;
    setStatus("Unsaved changes");
    clearTimeout(ed.saveTimer);
    ed.saveTimer = setTimeout(save, 600);
  }

  async function save() {
    clearTimeout(ed.saveTimer);
    if (ed.saving) {
      ed.saveAgain = true;
      return;
    }
    if (!ed.dirty) return;
    ed.saving = true;
    ed.dirty = false;
    setStatus("Saving…");
    try {
      const result = await put(`/api/catalogue/trees/${treeId}`, ed.tree);
      ed.problems = result.problems ?? [];
      setStatus(ed.dirty ? "Unsaved changes" : "Saved");
      renderOutline();
      renderProblems();
    } catch (e) {
      ed.dirty = true;
      setStatus(`Not saved: ${e.message}`, true);
    } finally {
      ed.saving = false;
      if (ed.saveAgain) {
        ed.saveAgain = false;
        save();
      }
    }
  }

  // ---- edits ---------------------------------------------------------------------------

  // Change a node's type, keeping what still fits: a DO becomes the first branch of a new
  // decision, and a decision keeps as many of its branches as the new type has.
  function setKind(path, kind) {
    change("kind", () => {
      const old = getAt(path);
      if (!kind) {
        setAt(path, null);
        return;
      }
      if (kind === "OUTPUT") {
        setAt(path, old?.kind === "OUTPUT" ? old : { kind: "OUTPUT", action: null });
        return;
      }
      const shape = ref.nodes[kind];
      const sameInputs = old && old.kind !== "OUTPUT" && ref.nodes[old.kind]?.input === shape.input;
      const keptInputs = sameInputs ? old.inputs : [];
      const children = Array.from({ length: shape.branches.length }, (_, i) => {
        if (old?.kind === "OUTPUT") return i === 0 ? old : null;
        return old?.children?.[i] ?? null;
      });
      setAt(path, {
        kind,
        inputs: Array.from({ length: shape.count }, (_, i) => keptInputs[i] ?? null),
        children,
      });
      ed.ui.open.set(pathKey(path), true);
    });
  }

  function setAction(path, name) {
    change("action", () => {
      setAt(path, name ? withArgs({ kind: "OUTPUT", action: name }, actions[name].args) : { kind: "OUTPUT", action: null });
    });
  }

  function setInput(path, index, name) {
    change("input", () => {
      getAt(path).inputs[index] = name ? withArgs({ name }, inputs[name].args) : null;
    });
  }

  // target(): the object holding args (an input or an OUTPUT node), looked up afresh each time.
  function setArg(target, index, value, coalesce = false) {
    change("arg", () => { target().args[index] = value; }, { coalesce });
  }

  function copyAt(path) {
    clipboard = structuredClone(getAt(path));
    renderClipboard();
    render();
  }

  function pasteAt(path) {
    if (!clipboard) return;
    change("paste", () => setAt(path, structuredClone(clipboard)));
  }

  // ---- rows ----------------------------------------------------------------------------

  function select(options, value, onchange, extra = {}) {
    return h("select", { ...extra, value: value ?? "", onchange: (e) => onchange(e.target.value || null) }, options);
  }

  const option = (value, text, title) => h("option", { value, title }, text);

  function kindSelect(path, node) {
    const kind = node?.kind ?? "";
    return select([
      option("", "empty", "An empty slot. The tree can't be played until it's filled."),
      KINDS.map(([value, text, doc]) => option(value, text, doc)),
    ], kind, (value) => setKind(path, value), {
      class: `kind-select ${kind || "EMPTY"}`,
      title: KINDS.find(([value]) => value === kind)?.[2] ?? "Choose what this node does",
    });
  }

  function actionSelect(path, node) {
    const known = new Set(ACTION_GROUPS.flatMap(([, names]) => names));
    const others = ref.actions.map((a) => a.name).filter((n) => !known.has(n));
    return select([
      node.action ? null : option("", "choose an action…"),
      ACTION_GROUPS.map(([label, names]) => h("optgroup", { label }, names.filter((n) => actions[n]).map((n) => option(n, n)))),
      others.length ? h("optgroup", { label: "Other" }, others.map((n) => option(n, n))) : null,
    ], node.action, (value) => setAction(path, value), { class: node.action ? "" : "unset" });
  }

  function inputSelect(path, nodeKind, index, item) {
    const wanted = ref.nodes[nodeKind].input;
    const choices = ref.inputs.filter((i) => i.kind === wanted);
    return select([
      item ? null : option("", `choose a ${wanted} input…`),
      choices.map((i) => option(i.name, i.name, i.doc)),
    ], item?.name, (value) => setInput(path, index, value), {
      class: item ? "" : "unset",
      title: item ? inputs[item.name]?.doc || item.name : `Choose a ${wanted} input`,
    });
  }

  function argEditors(spec, values, target) {
    return spec.map((kind, index) => argEditor(kind, values?.[index], target, index));
  }

  function argEditor(kind, value, target, index) {
    if (kind === "position") {
      const isXY = value && typeof value === "object";
      const pick = select([
        positions.map((p) => option(p, p)),
        option("XY_VALUE", "XY_VALUE (a tile)"),
      ], isXY ? "XY_VALUE" : value, (choice) =>
        setArg(target, index, choice === "XY_VALUE" ? { x: 0, y: 0 } : choice), { class: "arg" });
      if (!isXY) return pick;
      const coord = (axis) => h("input", {
        type: "number", min: "0", class: "coord", title: axis, value: String(value[axis]),
        onchange: (e) => setArg(target, index, { ...value, [axis]: Math.max(0, Math.round(Number(e.target.value) || 0)) }),
      });
      return h("span", { class: "xy" }, pick, "x", coord("x"), "y", coord("y"));
    }
    if (kind === "int") {
      return h("input", {
        type: "number", class: "arg number", value: String(value ?? 0),
        onchange: (e) => setArg(target, index, Math.round(Number(e.target.value) || 0)),
      });
    }
    if (kind === "activity") {
      return select(ACTION_GROUPS.map(([label, names]) =>
        h("optgroup", { label }, names.map((n) => option(n, n)))), value, (v) => setArg(target, index, v), { class: "arg" });
    }
    // A tree name: one of the trees this tree's owner can use.
    const names = [...new Set([...availableTrees(), value].filter(Boolean))];
    return select(names.map((n) => option(n, n)), value, (v) => setArg(target, index, v), { class: "arg" });
  }

  // A small ⋯ menu at the end of each row, so the buttons don't take up room on every line.
  function rowMenu(path) {
    const node = getAt(path);
    const item = (text, title, onclick, extra = {}) => h("button", { ...extra, title, onclick }, text);
    return h("details", { class: "row-menu" },
      h("summary", { title: "Focus, copy, paste or clear this branch" }, "⋯"),
      h("div", { class: "menu" },
        node && node.kind !== "OUTPUT" ? item("Focus on this branch", "Show just this branch", () => {
          ed.ui.focus = pathKey(path);
          ed.ui.open.set(pathKey(path), true);
          renderOutline();
        }) : null,
        item("Copy", "Copy this branch, to paste somewhere else", () => copyAt(path)),
        item("Paste", clipboard ? "Replace this branch with the copied one" : "Copy a branch first",
          () => pasteAt(path), { disabled: !clipboard }),
        node ? item("Clear", "Empty this slot (Ctrl+Z to undo)", () => setKind(path, null), { class: "danger" }) : null));
  }

  function row(view) {
    const { path, json: node } = view;
    const parts = [kindSelect(path, node)];
    if (node?.kind === "OUTPUT") {
      parts.push(actionSelect(path, node));
      if (node.action) {
        parts.push(argEditors(actions[node.action]?.args ?? [], node.args, () => getAt(path)));
      }
    } else if (node) {
      node.inputs.forEach((item, index) => {
        if (index) parts.push(h("span", { class: "vs", title: "The branch depends on how the first compares to the second" }, "vs"));
        parts.push(inputSelect(path, node.kind, index, item));
        if (item) parts.push(argEditors(inputs[item.name]?.args ?? [], item.args, () => getAt(path).inputs[index]));
      });
    }
    parts.push(rowMenu(path));
    return parts;
  }

  // ---- rendering -------------------------------------------------------------------------

  function problemsByPath() {
    const map = new Map();
    for (const p of ed.problems) {
      if (!Array.isArray(p.path)) continue;
      const key = pathKey(p.path);
      map.set(key, [...(map.get(key) ?? []), p.message]);
    }
    return map;
  }

  function renderOutline() {
    const view = fromJson(ed.tree.root);
    const marked = problemsByPath();
    const scroll = outline.querySelector(".tree")?.scrollLeft ?? 0;
    fill(outline, treeView(view, ed.ui, {
      keyOf: (node) => pathKey(node.path),
      row,
      rowClass: (node) => (marked.has(pathKey(node.path)) ? "problem" : ""),
      defaultOpen: (node, depth) => depth < 3,
      onChange: renderOutline,
      focusButton: false,
    }));
    for (const [key, messages] of marked) {
      const rowNode = outline.querySelector(`[data-key="${key}"]`);
      if (rowNode) rowNode.title = messages.join("\n");
    }
    const tree = outline.querySelector(".tree");
    if (tree) tree.scrollLeft = scroll;
    undoButton.disabled = !ed.history.length;
    redoButton.disabled = !ed.future.length;
  }

  // Another tree with this owner already has the name? A clash would stop the whole tree saving,
  // so a taken name isn't applied until it's changed.
  const nameTaken = (name, owner) => trees.some((t) => t.id !== treeId && t.owner === owner && t.name === name);

  function renderDetails() {
    const nameNote = h("span", { class: "error-text field-note" });
    const name = h("input", {
      value: ed.tree.name,
      oninput: (e) => {
        // Tree names can't have spaces, because CHANGE_TREE refers to them by name.
        const value = e.target.value.replace(/\s+/g, "-");
        if (value !== e.target.value) e.target.value = value;
        const taken = value && nameTaken(value, ed.tree.owner);
        nameNote.textContent = !value ? "A tree needs a name." : taken ? `There's already a tree called ${value}.` : "";
        name.classList.toggle("invalid", !value || taken);
        if (!value || taken) return;
        change("name", () => { ed.tree.name = value; }, { coalesce: true, refresh: "none" });
        title.textContent = value;
      },
      onchange: () => { if (!name.classList.contains("invalid")) render(); },
    });
    const owner = select([
      option("", "Default (every player can use it)"),
      players.map((p) => option(p.id, p.name)),
    ], ed.tree.owner, (value) => {
      if (nameTaken(ed.tree.name, value)) {
        showError(`${value ? players.find((p) => p.id === value)?.name : "The defaults"} already have a tree called ${ed.tree.name}. Rename this one first.`);
        owner.value = ed.tree.owner ?? "";
        return;
      }
      change("owner", () => { ed.tree.owner = value; });
    });
    const referrers = trees.filter((t) => t.id !== treeId && JSON.stringify(t.root ?? null).includes(`"CHANGE_TREE","args":["${tree.name}"]`));
    fill(details,
      h("div", { class: "card-head" }, h("h2", {}, "Tree")),
      h("div", { class: "fields" },
        h("label", {}, "Name", name, nameNote),
        h("label", {}, "Belongs to", owner)),
      h("p", { class: "hint" }, `${countNodes(fromJson(ed.tree.root))} nodes. `,
        "CHANGE_TREE can switch to this owner's trees and the default trees."),
      referrers.length ? h("p", { class: "hint" },
        `Switched to by ${referrers.map((t) => t.name).join(", ")}. Renaming this tree won't update them.`) : null,
      h("p", { class: "hint" }, "Saved games keep their own copy of a tree, so editing it doesn't change them."));
    return name;
  }

  function showProblem(path) {
    // Open every branch down to the problem, then scroll to it.
    ed.ui.focus = null;
    for (let i = 0; i <= path.length; i++) ed.ui.open.set(pathKey(path.slice(0, i)), true);
    renderOutline();
    const rowNode = outline.querySelector(`[data-key="${pathKey(path)}"]`);
    rowNode?.scrollIntoView({ block: "center", behavior: "smooth" });
    rowNode?.classList.add("flash");
  }

  function renderProblems() {
    const n = ed.problems.length;
    fill(problemsCard,
      h("div", { class: "card-head" }, h("h2", {}, "Ready to play?"),
        n ? h("span", { class: "badge warn" }, `${n} to fix`) : h("span", { class: "badge ok" }, "ready")),
      n ? h("ul", { class: "plain problems" }, ed.problems.map((p) => h("li", {},
        h("button", { class: "link", onclick: () => showProblem(p.path ?? []) }, p.where), `: ${p.message}`)))
        : h("p", {}, "Every slot is filled, so teams can start with this tree."));
  }

  function renderClipboard() {
    clipText.textContent = clipboard
      ? `Copied a branch of ${countNodes(fromJson(clipboard))} node${countNodes(fromJson(clipboard)) === 1 ? "" : "s"}`
      : "";
  }

  function render() {
    renderOutline();
    renderDetails();
    renderProblems();
    renderClipboard();
  }

  // ---- keys and leaving ------------------------------------------------------------------

  const onKey = (event) => {
    if (event.target.closest("input, textarea")) return;
    const mod = event.ctrlKey || event.metaKey;
    if (mod && event.key.toLowerCase() === "z") {
      event.preventDefault();
      event.shiftKey ? redo() : undo();
    } else if (mod && event.key.toLowerCase() === "y") {
      event.preventDefault();
      redo();
    }
  };
  const onUnload = (event) => {
    if (ed.dirty || ed.saving) event.preventDefault();
  };
  // Close an open row menu when clicking anywhere else.
  const onClick = (event) => {
    for (const menu of outline.querySelectorAll("details.row-menu[open]")) {
      if (!menu.contains(event.target)) menu.open = false;
    }
  };
  document.addEventListener("keydown", onKey);
  document.addEventListener("click", onClick);
  window.addEventListener("beforeunload", onUnload);

  render();
  if (query.get("new")) {
    const name = renderDetails();
    name.focus();
    name.select();
  }

  return () => {
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("click", onClick);
    window.removeEventListener("beforeunload", onUnload);
    if (ed.dirty) save().catch(() => showError("The last tree change wasn't saved."));
  };
}
