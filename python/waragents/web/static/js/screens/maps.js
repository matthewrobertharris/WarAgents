// Map editor: the list of maps (#/maps), and the editor for one map (#/maps/<id>).

import { get, post, put, remove } from "../api.js";
import { mapPreview } from "../board.js";
import { empty, fill, h, showError } from "../dom.js";
import * as editor from "./mapeditor.js";

// A new map is a single flat tile, ready to grow.
const NEW_MAP = {
  name: "New map", mode: "FIXED", maxAgents: 10, dirt: [[0]], food: [[0]],
  plants: [], starts: [], criteria: [{ type: "SURVIVE_TURNS", turns: 300 }],
};

function status(m) {
  if (m.error) return h("span", { class: "badge warn", title: m.error }, "can't load");
  if (m.problems?.length) {
    return h("span", { class: "badge warn", title: m.problems.join("\n") }, "not playable yet");
  }
  return h("span", { class: "badge ok" }, "ready");
}

async function list(root) {
  const grid = h("div", { class: "map-grid" });
  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Map editor"),
        h("p", { class: "hint" }, "Click a map to edit it. Maps can be any shape, and gaps are holes agents can't enter.")),
      h("div", { class: "head-actions" }, h("button", { class: "primary", onclick: create }, "New map"))),
    h("section", { class: "card" }, grid));

  async function create() {
    try {
      const made = await post("/api/catalogue/maps", NEW_MAP);
      location.hash = `#/maps/${made.id}?new=1`;
    } catch (e) {
      showError(e.message);
    }
  }

  function card(m) {
    const name = h("strong", {}, m.name);
    const title = h("div", { class: "map-title" }, name);
    const startRename = () => {
      const input = h("input", { value: m.name, class: "rename" });
      const save = async () => {
        const newName = input.value.trim();
        if (!newName || newName === m.name) return refresh();
        try {
          await put(`/api/catalogue/maps/${m.id}`, { ...m, name: newName });
        } catch (e) {
          showError(e.message);
        }
        refresh();
      };
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") save();
        if (e.key === "Escape") refresh();
      });
      fill(title, input, h("button", { class: "small primary", onclick: save }, "Save"),
        h("button", { class: "small", onclick: refresh }, "Cancel"));
      input.focus();
      input.select();
    };
    const playable = !m.error && !m.problems?.length;
    return h("div", { class: "map-card" },
      m.error
        ? h("div", { class: "preview broken" }, "Can't load")
        : h("a", { href: `#/maps/${m.id}`, title: "Edit this map" }, mapPreview(m, 200, 14)),
      title,
      h("span", { class: "hint" }, m.error ? m.error
        : `${m.width}×${m.height} · ${m.slots.length} slot${m.slots.length === 1 ? "" : "s"} · ${m.plants.length} plant${m.plants.length === 1 ? "" : "s"}`),
      status(m),
      h("div", { class: "card-actions" },
        m.error ? null : h("a", { class: "button small", href: `#/maps/${m.id}` }, "Edit"),
        m.error ? null : h("button", { class: "small", onclick: startRename }, "Rename"),
        playable
          ? h("a", { class: "button small primary", href: `#/new?map=${m.id}` }, "Play")
          : h("button", { class: "small", disabled: true, title: m.problems?.join("\n") ?? "" }, "Play"),
        h("button", {
          class: "small danger",
          onclick: async () => {
            if (!confirm(`Delete the map "${m.name}"? Saved games on it keep their own copy.`)) return;
            try {
              await remove(`/api/catalogue/maps/${m.id}`);
            } catch (e) {
              showError(e.message);
            }
            refresh();
          },
        }, "Delete")));
  }

  async function refresh() {
    const maps = await get("/api/catalogue/maps");
    fill(grid, maps.length ? maps.map(card) : empty("No maps yet. Make one with New map."));
  }
  await refresh();
}

export async function mount(root, [mapId], query) {
  if (mapId) return editor.mount(root, mapId, query);
  return list(root);
}
