// What trees cost, the same way as scenario.tree_cost and team_cost on the server: a decision
// costs what its inputs cost, an action costs a point (see /api/reference), and an empty slot is
// free. A team pays once for every tree it can reach with CHANGE_TREE.

function costs(ref) {
  return {
    inputs: Object.fromEntries(ref.inputs.map((i) => [i.name, i.cost ?? 1])),
    actions: Object.fromEntries(ref.actions.map((a) => [a.name, a.cost ?? 1])),
  };
}

export function treeCost(root, ref) {
  const { inputs, actions } = costs(ref);
  let total = 0;
  (function walk(node) {
    if (!node) return;
    if (node.kind === "OUTPUT") total += actions[node.action] ?? 1;
    for (const item of node.inputs ?? []) if (item) total += inputs[item.name] ?? 1;
    (node.children ?? []).forEach(walk);
  })(root);
  return total;
}

function switchesTo(root) {
  const names = new Set();
  (function walk(node) {
    if (!node) return;
    if (node.action === "CHANGE_TREE" && node.args?.[0]) names.add(node.args[0]);
    (node.children ?? []).forEach(walk);
  })(root);
  return [...names];
}

// available maps tree names to the trees the team can use. Returns {cost, trees: {name: cost}}.
export function teamCost(tree, available, ref) {
  const trees = {};
  const queue = [tree];
  while (queue.length) {
    const next = queue.pop();
    if (next.name in trees) continue;
    trees[next.name] = treeCost(next.root, ref);
    for (const name of switchesTo(next.root)) if (available[name]) queue.push(available[name]);
  }
  return { cost: Object.values(trees).reduce((a, b) => a + b, 0), trees };
}

// The trees a player can use by name: their own, hiding default trees with the same name.
export function usableTrees(trees, owner) {
  const usable = Object.fromEntries(trees.filter((t) => t.owner === null).map((t) => [t.name, t]));
  for (const t of trees) if (owner && t.owner === owner) usable[t.name] = t;
  return usable;
}
