// The catalogue: everything saved, by kind, plus importing old .map files.
// #/catalogue/<tab> opens a tab: maps, trees, players, games or import.

import { get, post, remove } from "../api.js";
import { mapPreview } from "../board.js";
import { empty, formatDay, h, showError } from "../dom.js";
import { countNodes, fromJson } from "../treeview.js";
import { gameList } from "./games.js";

const TABS = [["maps", "Maps"], ["trees", "Trees"], ["players", "Players"], ["games", "Games"], ["import", "Import .map"]];

function deleteButton(kind, item, refresh, label = item.name) {
  return h("button", {
    class: "small danger",
    onclick: async () => {
      if (!confirm(`Delete "${label}"? This can't be undone.`)) return;
      try {
        await remove(`/api/catalogue/${kind}/${item.id}`);
        await refresh();
      } catch (e) {
        showError(e.message);
      }
    },
  }, "Delete");
}

function table(headings, rows) {
  return h("div", { class: "table-wrap" }, h("table", { class: "list" },
    h("thead", {}, h("tr", {}, headings.map((t) => h("th", {}, t)))),
    h("tbody", {}, rows)));
}

async function mapsTab(body, refresh) {
  const maps = await get("/api/catalogue/maps");
  body.replaceChildren(maps.length ? table(["", "Map", "Size", "Slots", "Plants", "Mode", ""], maps.map((m) =>
    h("tr", {},
      h("td", { class: "thumb" }, m.error ? null : mapPreview(m, 90, 6)),
      h("td", {}, h("strong", {}, m.name), h("div", { class: "hint" }, m.id),
        m.error ? h("div", { class: "error-text" }, m.error) : null,
        m.problems?.length ? h("div", { class: "hint" }, `Not playable yet: ${m.problems.join("; ")}`) : null),
      h("td", {}, m.error ? "" : `${m.width}×${m.height}`),
      h("td", { class: "num" }, m.slots?.length ?? ""),
      h("td", { class: "num" }, m.plants?.length ?? ""),
      h("td", {}, m.mode ?? ""),
      h("td", { class: "actions" },
        m.error ? null : h("a", { class: "button small", href: `#/maps/${m.id}` }, "Edit"),
        m.error || m.problems?.length ? null : h("a", { class: "button small", href: `#/new?map=${m.id}` }, "Play"),
        deleteButton("maps", m, refresh)))))
    : empty("No maps yet. Make one in the map editor, or import a .map file."));
}

async function treesTab(body, refresh) {
  const [trees, players] = await Promise.all([get("/api/catalogue/trees"), get("/api/catalogue/players")]);
  const ownerName = (id) => (id === null ? "Default" : players.find((p) => p.id === id)?.name ?? `${id} (missing)`);
  body.replaceChildren(trees.length ? table(["Tree", "Owner", "Nodes", "Status", ""], trees.map((t) =>
    h("tr", {},
      h("td", {}, h("a", { href: `#/trees/${t.id}` }, h("strong", {}, t.name)), h("div", { class: "hint" }, t.id)),
      h("td", {}, ownerName(t.owner)),
      h("td", { class: "num" }, t.root ? countNodes(fromJson(t.root)) : 0),
      h("td", {}, t.error ? h("span", { class: "error-text" }, t.error)
        : t.problems.length ? h("span", { class: "badge warn" }, `${t.problems.length} to fix`)
          : h("span", { class: "badge ok" }, "ready")),
      h("td", { class: "actions" }, deleteButton("trees", t, refresh)))))
    : empty("No trees yet."));
}

async function playersTab(body, refresh) {
  const [players, trees] = await Promise.all([get("/api/catalogue/players"), get("/api/catalogue/trees")]);
  body.replaceChildren(
    h("p", { class: "hint" },
      "A player is a person. Their trees belong to them, and their colour is used for their teams. ",
      "Add and edit players on the ", h("a", { href: "#/players" }, "Players"), " screen."),
    players.length ? table(["Player", "Colour", "Starting tree", "Trees", "Joined", ""], players.map((p) =>
      h("tr", {},
        h("td", {}, h("a", { href: `#/players/${p.id}` }, h("strong", {}, p.name)), h("div", { class: "hint" }, p.id)),
        h("td", {}, p.colour ? h("span", { class: "team-tag" }, h("span", { class: "dot", style: `background:${p.colour}` }), p.colour) : ""),
        h("td", {}, p.startTree ?? ""),
        h("td", { class: "num" }, trees.filter((t) => t.owner === p.id).length),
        h("td", {}, formatDay(p.created)),
        h("td", { class: "actions" },
          h("a", { class: "button small", href: `#/players/${p.id}` }, "Open"),
          deleteButton("players", p, refresh)))))
      : empty("No players yet."));
}

async function gamesTab(body, refresh) {
  body.replaceChildren(gameList(await get("/api/catalogue/games"), refresh));
}

async function importTab(body) {
  const players = await get("/api/catalogue/players");
  const name = h("input", { placeholder: "Map name", required: true });
  const owner = h("select", {},
    h("option", { value: "" }, "Default trees (everyone)"), players.map((p) => h("option", { value: p.id }, p.name)));
  const text = h("textarea", { wrap: "off", placeholder: "height=5\nwidth=5\nfood=\n..." });
  text.spellcheck = false;  // h() skips false props
  const file = h("input", {
    type: "file", accept: ".map,.txt",
    onchange: async () => {
      const chosen = file.files[0];
      if (!chosen) return;
      text.value = await chosen.text();
      if (!name.value) name.value = chosen.name.replace(/\.[^.]+$/, "");
    },
  });
  const result = h("div");
  body.replaceChildren(
    h("p", { class: "hint" },
      "Turns a .map file from the Java version into a map plus one tree per tree= line. Each player in the file becomes a start slot. ",
      "Tree names that are already taken get a number added."),
    h("form", {
      class: "import",
      onsubmit: async (e) => {
        e.preventDefault();
        try {
          const done = await post("/api/catalogue/import", { text: text.value, name: name.value.trim(), owner: owner.value || null });
          result.replaceChildren(h("div", { class: "banner outcome" },
            "Imported the map ", h("a", { href: `#/new?map=${done.map}` }, done.map),
            ` and ${done.trees.length} tree${done.trees.length === 1 ? "" : "s"}: `,
            done.trees.map((id, i) => [i ? ", " : "", h("a", { href: `#/trees/${id}` }, id)])));
        } catch (err) {
          result.replaceChildren(h("div", { class: "banner error inline" }, err.message));
        }
      },
    },
    h("div", { class: "form-row" }, h("label", {}, "Name ", name), h("label", {}, "Trees belong to ", owner), file),
    text,
    h("div", { class: "form-row" }, h("button", { class: "primary" }, "Import"))),
    result);
}

const RENDER = { maps: mapsTab, trees: treesTab, players: playersTab, games: gamesTab, import: importTab };

export async function mount(root, [tab = "maps"]) {
  if (!RENDER[tab]) tab = "maps";
  const body = h("section", { class: "card" });
  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Catalogue"),
      h("p", { class: "hint" }, "Everything is stored as JSON files in python/catalogue, one file per item."))),
    h("nav", { class: "tabs big" }, TABS.map(([id, label]) =>
      h("a", { class: `tab${id === tab ? " current" : ""}`, href: `#/catalogue/${id}` }, label))),
    body);
  const refresh = () => RENDER[tab](body, refresh);
  await refresh();
}
