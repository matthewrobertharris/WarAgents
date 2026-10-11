// Watching a game (#/play/<id>, add ?turn=40 to jump ahead). Battles are already decided, so this
// is a replay, and it links back to the result. Sandbox games play out as you watch.

import { get } from "../api.js";
import { h } from "../dom.js";
import { mountViewer } from "../viewer.js";

export async function mount(root, [gameId], query) {
  const result = await get(`/api/results/${gameId}`).catch(() => null);
  return mountViewer(root, gameId, {
    title: result ? `Replay: ${result.name}` : undefined,
    endTurn: result?.turns,
    turn: Number(query.get("turn")) || 0,
    actions: [
      result ? h("a", { class: "button", href: `#/results/${gameId}` }, "Result") : null,
      h("a", { class: "button", href: "#/history" }, "History"),
    ],
  });
}
