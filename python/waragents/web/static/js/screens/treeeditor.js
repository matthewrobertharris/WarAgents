// Editing one decision tree (#/trees/<id>). The tree is the collapsible outline from
// treeview.js with a dropdown for every choice on each row:
//   - every row's first dropdown is an empty slot, an action (picking one makes the node a DO
//     with that action), or BOOLEAN, NUMERIC or POSITION
//   - a DO row then takes the action's argument, if any (CHANGE_TREE's tree, SET_PRIMARY's position)
//   - a BOOLEAN row picks a boolean input and has true/false branches
//   - a NUMERIC row picks two numeric inputs and branches on how the first compares to the second
//   - a POSITION row picks a position input and branches on which way that position is
//   - an input's arguments are a position, a whole number, an action or a tree name
// Each row's ⋯ menu can also restructure the tree: insert a decision above a node (the node
// becomes its first branch), swap a branch with its siblings, replace a decision with one of its
// branches, and cut, copy and paste branches (between trees too).
// Only what fits a slot is offered. Nothing is locked, but every input and action costs points,
// and the side panel shows the tree's cost against the player's budget, which grows with their
// level. Changes save themselves, and Ctrl+Z / Ctrl+Y undo and redo. Someone else's tree (a default tree,
// for a player who isn't an admin) opens read-only: they can try changes but not save them.

import { get, put, reference } from "../api.js";
import { teamCost, treeCost, usableTrees } from "../cost.js";
import { fill, h, showError } from "../dom.js";
import { isAdmin, loadUser, updateUser, user } from "../session.js";
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
  const canSave = isAdmin() || tree.owner === user().id;
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
  const costCard = h("section", { class: "card" });
  const problemsCard = h("section", { class: "card" });
  const clipText = h("span", { class: "hint" });
  root.append(
    h("div", { class: "page-head" },
      h("div", {}, title, h("p", { class: "hint" }, canSave ? "Changes save automatically. " : "", statusText)),
      h("div", { class: "head-actions" },
        query.get("tutorial") ? h("a", { class: "button primary", href: `#/training/${query.get("tutorial")}` }, "Back to the tutorial") : null,
        h("a", { class: "button", href: "#/trees" }, "All trees"))),
    canSave ? "" : h("p", { class: "banner note readonly" },
      "This is a default tree, so you can look and try changes but they won't be saved. ",
      "Duplicate it on the trees screen to make a copy of your own."),
    h("div", { class: "layout tree-layout" },
      h("section", { class: "card" },
        h("div", { class: "controls" }, undoButton, redoButton, clipText,
          h("span", { class: "hint status" }, "Each row's ⋯ menu can insert a decision above it, swap branches, and cut, copy and paste.")),
        outline),
      h("aside", { class: "side" }, details, costCard, problemsCard)));

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
    setStatus(canSave ? "Unsaved changes" : "Read-only: changes aren't saved");
    if (!canSave) return;
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
      // Saving can change whether your default tree is ready, which the home screen shows.
      if (user().startTree === ed.tree.name) loadUser();
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

  // Picking an action in a row's first dropdown makes the node a DO with that action, in one go.
  function setAction(path, name) {
    change("action", () => {
      setAt(path, withArgs({ kind: "OUTPUT", action: name }, actions[name].args));
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

  // Copy a branch and empty its slot, so it can be pasted somewhere else.
  function cutAt(path) {
    clipboard = structuredClone(getAt(path));
    renderClipboard();
    change("cut", () => setAt(path, null));
  }

  // ---- restructuring -------------------------------------------------------------------
  //
  // Which branches are open (and which one is focused) is remembered by path, so when a branch
  // moves, its open/closed state moves with it. move(path) gives a node's new path, or null if
  // the node is gone.

  function remapUi(move) {
    const parse = (key) => key.split(".").slice(1).map(Number);
    const open = new Map();
    for (const [key, value] of ed.ui.open) {
      const moved = move(parse(key));
      if (moved) open.set(pathKey(moved), value);
    }
    ed.ui.open = open;
    if (ed.ui.focus) {
      const moved = move(parse(ed.ui.focus));
      ed.ui.focus = moved ? pathKey(moved) : null;
    }
  }

  const startsWith = (p, prefix) => prefix.every((v, i) => p[i] === v);

  // Put a new decision above a node. The node, with everything under it, becomes the decision's
  // first branch (true, < or left), and its inputs are left to choose.
  function insertAbove(path, kind) {
    change("insert", () => {
      const shape = ref.nodes[kind];
      setAt(path, {
        kind,
        inputs: Array.from({ length: shape.count }, () => null),
        children: shape.branches.map((_, i) => (i === 0 ? getAt(path) : null)),
      });
      remapUi((p) => (startsWith(p, path) ? [...path, 0, ...p.slice(path.length)] : p));
      ed.ui.open.set(pathKey(path), true);
    });
  }

  // Swap two branches of the decision at parentPath, everything under them included.
  function swapBranches(parentPath, i, j) {
    change("swap", () => {
      const parent = getAt(parentPath);
      [parent.children[i], parent.children[j]] = [parent.children[j], parent.children[i]];
      const depth = parentPath.length;
      remapUi((p) => {
        if (!startsWith(p, parentPath) || p.length <= depth || (p[depth] !== i && p[depth] !== j)) return p;
        return [...parentPath, p[depth] === i ? j : i, ...p.slice(depth + 1)];
      });
    });
  }

  // Replace a decision with one of its branches, dropping the decision and its other branches.
  function keepBranch(path, index) {
    change("unwrap", () => {
      setAt(path, getAt(path).children[index]);
      const depth = path.length;
      remapUi((p) => {
        if (!startsWith(p, path)) return p;           // somewhere else in the tree
        if (p.length === depth) return null;          // the decision itself, now gone
        return p[depth] === index ? [...path, ...p.slice(depth + 1)] : null;  // the kept branch moves up
      });
    });
  }

  // ---- rows ----------------------------------------------------------------------------

  function select(options, value, onchange, extra = {}) {
    return h("select", { ...extra, value: value ?? "", onchange: (e) => onchange(e.target.value || null) }, options);
  }

  const option = (value, text, title) => h("option", { value, title }, text);

  // A row's first dropdown says what the node does: an action (so DO and its action are one
  // pick), or BOOLEAN, NUMERIC or POSITION, whose inputs are chosen in the dropdowns after it.
  function kindSelect(path, node) {
    const kind = node?.kind ?? "";
    const current = kind === "OUTPUT" ? `OUTPUT:${node.action ?? ""}` : kind;
    const known = new Set(ACTION_GROUPS.flatMap(([, names]) => names));
    const others = ref.actions.map((a) => a.name).filter((n) => !known.has(n));
    const doOption = (n) => option(`OUTPUT:${n}`, n, actions[n]?.doc);
    return select([
      option("", "empty", "An empty slot. The tree can't be played until it's filled."),
      kind === "OUTPUT" && !node.action ? option("OUTPUT:", "DO: choose an action…") : null,
      ACTION_GROUPS.map(([label, names]) => h("optgroup", { label: `DO · ${label}` },
        names.filter((n) => actions[n]).map(doOption))),
      others.length ? h("optgroup", { label: "DO · Other" }, others.map(doOption)) : null,
      h("optgroup", { label: "Decisions" },
        KINDS.filter(([k]) => k !== "OUTPUT").map(([value, text, doc]) => option(value, text, doc))),
    ], current, (value) => (value.startsWith("OUTPUT:") ? setAction(path, value.slice(7)) : setKind(path, value || null)), {
      class: `kind-select ${kind || "EMPTY"}`,
      title: kind === "OUTPUT" ? actions[node.action]?.doc ?? "Choose an action"
        : KINDS.find(([value]) => value === kind)?.[2] ?? "Choose an action, or a decision that picks a branch",
    });
  }

  function inputSelect(path, nodeKind, index, item) {
    const wanted = ref.nodes[nodeKind].input;
    const choices = ref.inputs.filter((i) => i.kind === wanted);
    return select([
      item ? null : option("", `choose a ${wanted} input…`),
      choices.map((i) => option(i.name, `${i.name} · ${i.cost}`, `${i.doc ? `${i.doc} ` : ""}Costs ${i.cost} point${i.cost === 1 ? "" : "s"}.`)),
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

  // An open menu is placed against the window rather than the outline, which scrolls and would
  // cut it off: below its ⋯ if there's room, otherwise above, and never off the right edge.
  function placeMenu(event) {
    const details = event.currentTarget;
    if (!details.open) return;
    const menu = details.querySelector(".menu");
    const at = details.querySelector("summary").getBoundingClientRect();
    menu.style.left = `${Math.max(8, Math.min(at.left, innerWidth - menu.offsetWidth - 8))}px`;
    const below = innerHeight - at.bottom;
    if (below < menu.offsetHeight + 8 && at.top > below) {
      menu.style.top = "";
      menu.style.bottom = `${innerHeight - at.top + 2}px`;
      menu.style.maxHeight = `${at.top - 16}px`;
    } else {
      menu.style.bottom = "";
      menu.style.top = `${at.bottom + 2}px`;
      menu.style.maxHeight = `${below - 16}px`;
    }
  }

  // A small ⋯ menu at the end of each row, so the buttons don't take up room on every line.
  function rowMenu(path) {
    const node = getAt(path);
    const item = (text, title, onclick, extra = {}) => h("button", { ...extra, title, onclick }, text);
    const label = (text) => h("span", { class: "menu-label" }, text);
    const decision = node && node.kind !== "OUTPUT";
    const parent = path.length ? getAt(path.slice(0, -1)) : null;
    const branches = parent ? ref.nodes[parent.kind].branches : [];
    const here = path.at(-1);
    return h("details", { class: "row-menu", ontoggle: placeMenu },
      h("summary", { title: "Focus, copy, paste, move or clear this branch" }, "⋯"),
      h("div", { class: "menu" },
        decision ? item("Focus on this branch", "Show just this branch", () => {
          ed.ui.focus = pathKey(path);
          ed.ui.open.set(pathKey(path), true);
          renderOutline();
        }) : null,
        item("Copy", "Copy this branch, to paste somewhere else", () => copyAt(path)),
        node ? item("Cut", "Copy this branch and empty its slot, to move it somewhere else", () => cutAt(path)) : null,
        item("Paste", clipboard ? "Replace this branch with the copied one" : "Copy a branch first",
          () => pasteAt(path), { disabled: !clipboard }),

        node ? [label("Insert a decision above"),
          KINDS.filter(([kind]) => kind !== "OUTPUT").map(([kind, text]) => {
            const first = ref.nodes[kind].branches[0];
            return item(`${text} (this goes under “${first}”)`,
              `Put a new ${text} node here, with this branch as its “${first}” branch`, () => insertAbove(path, kind));
          })] : null,

        branches.length > 1 ? [label(`Swap this “${branches[here]}” branch with`),
          branches.map((name, i) => (i === here ? null : item(`the “${name}” branch`,
            `Swap the “${branches[here]}” and “${name}” branches, with everything under them`,
            () => swapBranches(path.slice(0, -1), here, i))))] : null,

        decision && node.children.some(Boolean) ? [label("Replace this decision with its"),
          ref.nodes[node.kind].branches.map((name, i) => (node.children[i] ? item(`“${name}” branch`,
            `Drop this question and the other branches, keeping just the “${name}” branch`,
            () => keepBranch(path, i)) : null))] : null,

        node ? item("Clear", "Empty this slot (Ctrl+Z to undo)", () => setKind(path, null), { class: "danger" }) : null));
  }

  function row(view) {
    const { path, json: node } = view;
    const parts = [kindSelect(path, node)];
    if (node?.kind === "OUTPUT") {
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
    renderCost();
  }

  // The tree's cost, and for a player's own tree, how it fits their budget and whether it's
  // their default tree (the one that plays for them when someone else picks them to fight).
  function renderCost() {
    const own = ed.tree.owner !== null && ed.tree.owner === user().id;
    const available = { ...usableTrees(trees, ed.tree.owner), [ed.tree.name]: ed.tree };
    const team = teamCost(ed.tree, available, ref);
    const others = Object.keys(team.trees).filter((n) => n !== ed.tree.name);
    const budget = user().budget;
    const over = own && team.cost > budget;
    const isDefault = own && user().startTree === ed.tree.name;

    async function makeDefault() {
      try {
        updateUser(await put("/api/me", { startTree: ed.tree.name }));
        renderCost();
      } catch (e) {
        showError(e.message);
      }
    }

    fill(costCard,
      h("div", { class: "card-head" }, h("h2", {}, "Cost"),
        own ? h("span", { class: `badge ${over ? "warn" : "ok"}` }, `${team.cost} / ${budget} points`)
          : h("span", { class: "badge" }, `${team.cost} points`)),
      own ? h("div", { class: "meter", title: `${team.cost} of ${budget} points` },
        h("span", { class: over ? "over" : "", style: `width:${Math.min(100, (100 * team.cost) / budget)}%` })) : null,
      h("p", { class: "hint" }, others.length
        ? `This tree costs ${treeCost(ed.tree.root, ref)} points, and ${team.cost} with ${others.join(", ")}, which it switches to.`
        : "Each input costs the points shown next to it, and each action costs 1."),
      own ? h("p", { class: "hint" }, over
        ? `That's over your budget of ${budget} points at level ${user().level}, so it can't go into battle. Simplify it, or level up for more points.`
        : `Your budget is ${budget} points at level ${user().level}. Each level adds more.`)
        : h("p", { class: "hint" }, "Default trees aren't limited by a budget. Your own copy of one is."),
      own ? (isDefault
        ? h("p", { class: "default-note" }, "This is your default tree: it defends you when other players pick you to fight.")
        : h("button", { class: "small", onclick: makeDefault, disabled: over || ed.problems.length > 0,
          title: over ? "It's over your budget" : ed.problems.length ? "Finish it first" : "" }, "Make this my default tree"))
        : null);
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
    const ownerName = ed.tree.owner === null ? "Default (every player can use it)"
      : ed.tree.owner === user().id ? "You" : players.find((p) => p.id === ed.tree.owner)?.name ?? ed.tree.owner;
    const owner = !isAdmin() ? h("span", { class: "owner-name" }, ownerName) : select([
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
  // A menu placed against the window would drift from its row when anything scrolls, so close it.
  const onScroll = (event) => {
    if (event.target.closest?.(".row-menu")) return;
    for (const menu of outline.querySelectorAll("details.row-menu[open]")) menu.open = false;
  };
  document.addEventListener("keydown", onKey);
  document.addEventListener("click", onClick);
  document.addEventListener("scroll", onScroll, true);
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
    document.removeEventListener("scroll", onScroll, true);
    window.removeEventListener("beforeunload", onUnload);
    if (ed.dirty) save().catch(() => showError("The last tree change wasn't saved."));
  };
}
