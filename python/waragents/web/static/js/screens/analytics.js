// Analytics (#/analytics): how your trees have done over your finished games, as charts you can
// filter down. The filters live in the address (#/analytics?tree=raid&mode=season), so a view can
// be bookmarked. Clicking a bar in any breakdown filters everything by it; clicking it again
// clears that filter. Picking one tree adds its versions and a heat map of which of its nodes
// your agents actually used.

import { get } from "../api.js";
import { chartCard, compact, dataTable, legend, lineChart, pairedBars, percent, shareMeter, stackedBars, stackedColumns } from "../charts.js";
import { empty, fill, formatDate, formatDay, h } from "../dom.js";
import { MODES, modeBadge, ordinal, plural } from "../format.js";
import { fromJson, newUi, treeView } from "../treeview.js";

const KEYS = ["since", "until", "mode", "map", "tree", "version", "opponent", "outcome", "season"];
const RESULTS = [{ key: "wins", label: "Wins", series: 1 }, { key: "losses", label: "Losses", series: 2 }];
const ACTIONS = [{ key: "succeeded", label: "Worked", series: 1 }, { key: "failed", label: "Failed", series: 2 }];
const SIDES = [{ label: "You", series: 1 }, { label: "Opponents", series: 2 }];
const PRESETS = [["", "All time"], ["7", "Last 7 days"], ["30", "Last 30 days"], ["90", "Last 90 days"], ["custom", "Custom dates"]];

const isoDay = (date) => date.toISOString().slice(0, 10);
const daysAgo = (n) => isoDay(new Date(Date.now() - (n - 1) * 86400000));

// Win and loss counts for the stacked bars.
const withLosses = (rows) => rows.map((r) => ({ ...r, losses: r.games - r.wins }));
const resultEnd = (r) => `${percent(r.winRate)} of ${r.games}`;
const resultTip = (r) => [
  { value: percent(r.winRate), label: "win rate" },
  { value: r.wins, label: "wins", series: 1 },
  { value: r.games - r.wins, label: "losses", series: 2 },
  ...(r.avgPlace !== null && r.avgPlace !== undefined ? [{ value: r.avgPlace, label: "average place" }] : []),
];
const resultTable = (rows, heading) => dataTable(rows, [
  [heading, (r) => r.label], ["Games", (r) => r.games, true], ["Wins", (r) => r.wins, true],
  ["Win rate", (r) => percent(r.winRate), true], ["Average place", (r) => r.avgPlace ?? "–", true]]);

function bucketLabel(start, bucket) {
  const date = new Date(`${start}T00:00:00`);
  if (bucket === "month") return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
  const day = date.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return bucket === "week" ? `w/c ${day}` : day;
}

function bucketRange(start, bucket) {
  const from = new Date(`${start}T00:00:00Z`);
  const to = new Date(from);
  if (bucket === "week") to.setUTCDate(to.getUTCDate() + 6);
  if (bucket === "month") to.setUTCMonth(to.getUTCMonth() + 1, 0);
  return [isoDay(from), isoDay(to)];
}

function resultText(game) {
  if (game.teams <= 1) return game.won ? "Completed" : "Failed";
  if (game.won) return game.place === 1 ? "Won" : "Shared win";
  return `${ordinal(game.place)} of ${game.teams}`;
}

export async function mount(root, _params, query) {
  const filters = Object.fromEntries(KEYS.map((k) => [k, query.get(k) ?? ""]));
  const options = await get("/api/analytics/options");
  let request = 0;
  let datePreset = filters.since && !filters.until
    ? (PRESETS.find(([days]) => days && days !== "custom" && daysAgo(Number(days)) === filters.since)?.[0] ?? "custom")
    : filters.since || filters.until ? "custom" : "";
  const treeUis = new Map();

  const bar = h("div", { class: "filters", role: "group", "aria-label": "Filters" });
  const body = h("div", { class: "analytics-body" });
  const exportLink = h("a", {
    class: "button export-link", download: "",
    title: "Every turn of every game that matches the filters (up to 500), as CSV files in a zip, to analyse yourself",
  }, "Export these games");

  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Analytics"),
        h("p", { class: "hint" }, "How your trees have done in your finished games, and what your opponents did. ",
          "Click any bar to filter everything by it.")),
      options.trees.length ? h("div", { class: "head-actions" }, exportLink) : null),
    bar, body);

  if (!options.trees.length) {
    fill(body, h("section", { class: "card" }, empty(
      "No finished games yet. Play a tutorial in Training or a battle, and your stats will appear here.")));
    return;
  }

  const query_ = () => {
    const params = new URLSearchParams();
    for (const k of KEYS) if (filters[k]) params.set(k, filters[k]);
    return params.toString();
  };

  const syncExport = () => { exportLink.href = `/api/analytics/export${query_() ? `?${query_()}` : ""}`; };

  function set(changes) {
    Object.assign(filters, changes);
    if ("tree" in changes) filters.version = "";
    history.replaceState(null, "", `#/analytics${query_() ? `?${query_()}` : ""}`);
    syncExport();
    renderFilters();
    load();
  }

  const toggle = (key, value) => set({ [key]: filters[key] === value ? "" : value });

  // ---- the filter row ---------------------------------------------------------------------

  function select(label, key, choices, { disabled = false } = {}) {
    return h("label", { class: `filter${filters[key] ? " active" : ""}` },
      h("span", { class: "filter-label" }, label),
      h("select", {
        disabled, value: filters[key],
        onchange: (e) => set({ [key]: e.target.value }),
      }, h("option", { value: "" }, "All"), choices.map(([value, text]) => h("option", { value }, text))));
  }

  function renderFilters() {
    const tree = options.trees.find((t) => t.key === filters.tree);
    const dates = h("label", { class: `filter${filters.since || filters.until ? " active" : ""}` },
      h("span", { class: "filter-label" }, "When"),
      h("select", {
        value: datePreset,
        onchange: (e) => {
          datePreset = e.target.value;
          if (datePreset === "custom") renderFilters();
          else set({ since: datePreset ? daysAgo(Number(datePreset)) : "", until: "" });
        },
      }, PRESETS.map(([value, text]) => h("option", { value }, text))));
    const custom = datePreset === "custom" ? h("span", { class: "filter custom-dates" },
      h("input", { type: "date", value: filters.since, "aria-label": "From", onchange: (e) => set({ since: e.target.value }) }),
      h("span", { class: "hint" }, "to"),
      h("input", { type: "date", value: filters.until, "aria-label": "To", onchange: (e) => set({ until: e.target.value }) }))
      : null;
    const any = KEYS.some((k) => filters[k]);
    fill(bar,
      dates, custom,
      select("Mode", "mode", options.modes.map((m) => [m.key, m.label])),
      select("Tree", "tree", options.trees.map((t) => [t.key, t.label])),
      select("Version", "version", (tree?.versions ?? []).map((v) => [v.key, `${v.label} · ${formatDay(v.firstPlayed)}`]),
        { disabled: !tree }),
      select("Map", "map", options.maps.map((m) => [m.key, m.label])),
      options.opponents.length ? select("Opponent", "opponent", options.opponents.map((o) => [o.key, o.label])) : null,
      select("Result", "outcome", [["win", "Wins"], ["loss", "Losses"]]),
      options.seasons.length ? select("Season", "season", options.seasons.map((s) => [s.key, s.label])) : null,
      any ? h("button", { class: "small", type: "button", onclick: () => {
        datePreset = "";
        set(Object.fromEntries(KEYS.map((k) => [k, ""])));
      } }, "Clear filters") : null);
  }

  // ---- the charts ---------------------------------------------------------------------------

  async function load() {
    const mine = ++request;
    body.classList.add("loading");
    try {
      const qs = query_();
      const [summary, nodes] = await Promise.all([
        get(`/api/analytics${qs ? `?${qs}` : ""}`),
        filters.tree ? get(`/api/analytics/nodes?${qs}`).catch(() => null) : Promise.resolve(null),
      ]);
      if (mine !== request) return;
      render(summary, nodes);
    } finally {
      if (mine === request) body.classList.remove("loading");
    }
  }

  function breakdown(title, rows, key, heading, note) {
    const data = withLosses(rows);
    return chartCard({
      title, note, legendFor: legend(RESULTS),
      empty: data.length ? null : empty("Nothing to show."),
      chart: () => stackedBars({ rows: data, series: RESULTS, end: resultEnd, tip: resultTip,
        selected: filters[key] || null, onSelect: (r) => toggle(key, r.key) }),
      table: () => resultTable(data, heading),
    });
  }

  function render(summary, nodes) {
    const k = summary.kpis;
    if (!k.games) {
      fill(body, h("section", { class: "card" }, empty("None of your finished games match these filters.")));
      return;
    }
    const tiles = h("div", { class: "kpis" },
      h("div", { class: "kpi hero" }, h("span", { class: "kpi-label" }, "Win rate"),
        h("span", { class: "kpi-value" }, percent(k.winRate)),
        h("span", { class: "kpi-sub" }, `${k.wins} of ${plural(k.games, "game")}`)),
      kpi("Average place", k.avgPlace ?? "–"),
      kpi("Average length", k.avgTurns === null ? "–" : `${compact(k.avgTurns)} turns`),
      kpi("Kills / deaths", `${compact(k.kills)} / ${compact(k.deaths)}`),
      kpi("Actions that worked", percent(k.successRate), `of ${compact(k.decisions)} decisions`),
      kpi("Confused", percent(k.confusedRate), "of decisions"),
      kpi("Account XP earned", compact(k.xp)),
      k.counted < k.games ? h("p", { class: "hint kpi-note" },
        `${k.games - k.counted} older game(s) haven't been counted yet, so only win rates include them.`) : null);

    const over = summary.overTime;
    const points = over.points.map((p) => ({ ...p, losses: p.games - p.wins, label: bucketLabel(p.start, over.bucket) }));
    const time = chartCard({
      title: "Results over time", wide: true, legendFor: legend(RESULTS),
      note: `Games per ${over.bucket}. Click a column to look at just that ${over.bucket}.`,
      chart: () => stackedColumns({ points, series: RESULTS,
        tip: (p) => [{ value: percent(p.winRate), label: "win rate" }, { value: p.wins, label: "wins", series: 1 },
          { value: p.losses, label: "losses", series: 2 }],
        onSelect: (p) => {
          const [since, until] = bucketRange(p.start, over.bucket);
          datePreset = "custom";
          set({ since, until });
        } }),
      table: () => dataTable(points, [["From", (p) => p.label], ["Games", (p) => p.games, true],
        ["Wins", (p) => p.wins, true], ["Win rate", (p) => percent(p.winRate), true]]),
    });

    const versions = summary.byVersion ? chartCard({
      title: "By version", legendFor: legend(RESULTS),
      note: "Each edit of the tree that played is a new version. Did your last change help?",
      chart: () => stackedBars({ rows: withLosses(summary.byVersion).map((v) => ({ ...v, label: `${v.label} · ${formatDay(v.firstPlayed)}` })),
        series: RESULTS, end: resultEnd, tip: resultTip, selected: filters.version || null,
        onSelect: (r) => toggle("version", r.key) }),
      table: () => resultTable(withLosses(summary.byVersion), "Version"),
    }) : null;

    const you = summary.you;
    const them = summary.opponents;
    const rivals = them.teams > 0;
    const noRivals = () => empty("There were no opponents in these games.");
    const actionCard = (title, side, note) => chartCard({
      title, note, legendFor: legend(ACTIONS),
      empty: side.actions.length ? null : side === them && !rivals ? noRivals() : empty("No actions counted yet."),
      chart: () => stackedBars({ rows: side.actions, series: ACTIONS,
        end: (a) => `${compact(a.succeeded + a.failed)}`,
        tip: (a) => [{ value: compact(a.succeeded), label: "worked", series: 1 }, { value: compact(a.failed), label: "failed", series: 2 },
          { value: percent(a.succeeded / Math.max(1, a.succeeded + a.failed)), label: "worked" }] }),
      table: () => dataTable(side.actions, [["Action", (a) => a.label], ["Worked", (a) => a.succeeded, true],
        ["Failed", (a) => a.failed, true]]),
    });

    const MEASURES = [["Kills", "kills"], ["Deaths", "deaths"], ["Damage dealt", "damageDealt"], ["Damage taken", "damageTaken"],
      ["Attacks blocked", "blocks"], ["Food eaten", "foodEaten"], ["Agents born", "births"], ["Most agents at once", "peakAgents"]];
    const versus = [
      ...MEASURES.map(([label, key]) => ({ label, a: you.averages[key], b: them.averages[key] })),
      { label: "Actions that worked", a: you.successRate, b: them.successRate, format: percent },
      { label: "Decisions confused", a: you.confusedRate, b: them.confusedRate, format: percent },
    ];
    const versusCard = chartCard({
      title: "You against your opponents", legendFor: legend(SIDES), wide: true,
      note: `Per team, per game: your ${plural(you.teams, "team")} against ${plural(them.teams, "opposing team")}. `
        + "Their trees are private, but what their agents did is fair game.",
      empty: rivals ? null : noRivals(),
      chart: () => pairedBars({ rows: versus, labels: ["You", "Opponents"] }),
      table: () => dataTable(versus, [["Per team, per game", (r) => r.label],
        ["You", (r) => (r.format ?? compact)(r.a), true], ["Opponents", (r) => (r.format ?? compact)(r.b), true]]),
    });

    const tl = summary.timeline;
    const timelineCard = (title, field, label, note) => {
      const lines = [{ label: "You", values: tl.you[field], series: 1 },
        ...(rivals ? [{ label: "Opponents (per team)", values: tl.opponents[field], series: 2 }] : [])];
      return chartCard({
        title, note, legendFor: rivals ? legend(SIDES, "line") : null,
        empty: tl.turns.length ? null : empty("No games counted yet."),
        chart: () => lineChart({ xs: tl.turns, lines,
          tip: (i) => [
            ...lines.map((l) => ({ value: l.values[i] === null ? "–" : compact(l.values[i]), label: l.label, series: l.series })),
            { value: tl.you.games[i], label: "games still going" }] }),
        table: () => dataTable(tl.turns.map((_, i) => i), [["Turn", (i) => tl.turns[i], true],
          ...lines.map((l) => [l.label, (i) => l.values[i] ?? "–", true]), ["Games still going", (i) => tl.you.games[i], true]]),
      });
    };

    fill(body, tiles, h("div", { class: "chart-grid" },
      time,
      breakdown("By tree", summary.byTree, "tree", "Tree", "Your tree at the start of each game. Pick one to see its versions and nodes."),
      versions,
      breakdown("By map", summary.byMap, "map", "Map"),
      summary.byOpponent.length ? breakdown("By opponent", summary.byOpponent, "opponent", "Opponent",
        "Games with that team in. Practice teams are bots.") : null,
      breakdown("By mode", summary.byMode, "mode", "Mode"),
      versusCard,
      h("div", { class: "chart-pair wide" },
        timelineCard("Agents alive", "agents", "agents",
          "Agents at the end of each turn, per team, averaged over the games still going."),
        timelineCard("Health", "health", "total health", "Their total health at each turn, averaged the same way.")),
      h("div", { class: "chart-pair wide" },
        actionCard("What your agents did", you,
          "Every decision ends in an action. Failed ones (a move into a wall, an attack on nobody) waste a turn."),
        actionCard("What your opponents' agents did", them, "The same, for the teams you played against.")),
      nodeCard(nodes),
      gamesCard(summary.games)));
  }

  const kpi = (label, value, sub) => h("div", { class: "kpi" },
    h("span", { class: "kpi-label" }, label), h("span", { class: "kpi-value" }, value),
    sub ? h("span", { class: "kpi-sub" }, sub) : null);

  // ---- a tree's nodes as a heat map ---------------------------------------------------------------

  function nodeCard(nodes) {
    if (!filters.tree) {
      return h("section", { class: "card chart-card wide" }, h("div", { class: "chart-head" }, h("h2", {}, "Which nodes fire")),
        empty("Pick a tree (in the filters or the By tree chart) to see how often your agents took each branch."));
    }
    if (!nodes) {
      return h("section", { class: "card chart-card wide" }, h("div", { class: "chart-head" }, h("h2", {}, "Which nodes fire")),
        empty("No counted games of this tree match the filters."));
    }
    const trees = [...nodes.trees].sort((a, b) => (a.name === nodes.startTree ? -1 : b.name === nodes.startTree ? 1 : a.name.localeCompare(b.name)));
    const total = Object.values(nodes.visits).reduce((sum, v) => sum + (v["0"]?.visits ?? 0), 0);
    const holder = h("div", { class: "heat-trees" });

    const draw = () => fill(holder, trees.map((tree) => {
      const visits = nodes.visits[tree.name] ?? {};
      const ui = treeUis.get(`${nodes.version}:${tree.name}`) ?? newUi();
      treeUis.set(`${nodes.version}:${tree.name}`, ui);
      const row = (node) => {
        const v = visits[node.id] ?? { visits: 0, confused: 0 };
        const share = total ? v.visits / total : 0;
        return [
          h("span", { class: `kind ${node.kind}` }, node.kind === "OUTPUT" ? "DO" : node.kind),
          h("span", { class: "label" }, node.label),
          h("span", { class: `heat${v.visits ? "" : " unused"}`, title: `${v.visits} visits, ${percent(share)} of decisions` },
            v.confused ? h("span", { class: "badge bad" }, `⚠ ${compact(v.confused)} confused`) : h("span"),
            shareMeter(share), h("span", { class: "heat-value" }, v.visits ? percent(share) : "never"),
            h("span", { class: "heat-count" }, v.visits ? compact(v.visits) : "")),
        ];
      };
      return h("div", { class: "heat-tree" },
        h("h3", { class: "sub" }, tree.name, tree.name === nodes.startTree ? h("span", { class: "hint" }, " (starts here)") : null),
        treeView(fromJson(tree.root), ui, {
          row, onChange: draw,
          defaultOpen: (node, depth) => depth < 8 && (visits[node.id]?.visits ?? 0) > 0,
        }));
    }));
    draw();
    return h("section", { class: "card chart-card wide" },
      h("div", { class: "chart-head" }, h("h2", {}, `Which nodes fire: ${nodes.versionLabel ?? ""}`)),
      h("p", { class: "hint chart-note" },
        `Over ${plural(nodes.counted, "counted game")} of this version. Each bar is the share of all ${compact(total)} decisions that `,
        "passed through the node. Branches never taken are closed. Node numbers change when a tree is edited, so this shows one version at a time.",
        nodes.counted < nodes.games ? ` ${nodes.games - nodes.counted} game(s) haven't been counted yet.` : ""),
      holder);
  }

  // ---- the games ----------------------------------------------------------------------------

  function gamesCard(games) {
    return h("section", { class: "card chart-card wide" },
      h("div", { class: "chart-head" }, h("h2", {}, games.length === 50 ? "The latest 50 games" : plural(games.length, "game"))),
      h("div", { class: "table-wrap" }, h("table", { class: "data" },
        h("thead", {}, h("tr", {}, ["When", "Mode", "Map", "Tree", "Against", "Result", "Turns", "Kills / deaths", "XP", ""]
          .map((t, i) => h("th", { class: i >= 6 && i <= 8 ? "num" : "" }, t)))),
        h("tbody", {}, games.map((g) => h("tr", {},
          h("td", { class: "hint" }, formatDate(g.created)),
          h("td", {}, MODES[g.mode] ? modeBadge(g.mode) : g.mode),
          h("td", {}, g.mapName),
          h("td", {}, g.treeName, g.versionLabel ? h("span", { class: "hint" }, ` ${g.versionLabel}`) : null),
          h("td", {}, g.opponents ?? h("span", { class: "hint" }, "nobody")),
          h("td", {}, h("span", { class: g.won ? "good-text" : "" }, resultText(g))),
          h("td", { class: "num" }, g.turns),
          h("td", { class: "num" }, g.kills === null ? "–" : `${g.kills} / ${g.deaths}`),
          h("td", { class: "num" }, g.xp ? `+${g.xp}` : ""),
          h("td", {}, h("a", { class: "button small", href: `#/results/${g.id}` }, "Result"))))))));
  }

  syncExport();
  renderFilters();
  await load();
}
