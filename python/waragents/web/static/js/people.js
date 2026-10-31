// Pieces for showing other players: an avatar, a player card, and the button that adds them as a
// friend (or shows how you stand: request sent, waiting for your answer, or friends).

import { post, remove } from "./api.js";
import { PALETTE } from "./colours.js";
import { h, showError } from "./dom.js";
import { loadUser } from "./session.js";

const initials = (name) => (name ?? "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";

export function avatar(player, big = false) {
  return h("span", { class: `avatar${big ? " big" : ""}`, style: `background:${player.colour ?? PALETTE[6]}` }, initials(player.name));
}

// Tell the top bar the signed-in player has changed, so it can update the friend request count.
export async function userChanged() {
  await loadUser();
  window.dispatchEvent(new Event("waragents:user"));
}

// Do a friend request call, then refresh the top bar and call done().
async function act(call, done) {
  try {
    await call();
    await userChanged();
    done();
  } catch (e) {
    showError(e.message);
  }
}

// The controls for how you stand with a player. friendship is "none", "sent", "received",
// "friends" or "you". done() runs after any change, to redraw.
export function friendControls(player, done) {
  const add = () => act(() => post("/api/friends", { player: player.id }), done);
  const accept = () => act(() => post(`/api/friends/${player.id}/accept`), done);
  const drop = (question) => () => {
    if (question && !confirm(question)) return;
    act(() => remove(`/api/friends/${player.id}`), done);
  };
  switch (player.friendship) {
    case "none":
      return h("button", { class: "primary", onclick: add }, "Add friend");
    case "sent":
      return [h("span", { class: "badge" }, "Request sent"),
        h("button", { class: "small", onclick: drop(null) }, "Cancel request")];
    case "received":
      return [h("button", { class: "primary", onclick: accept }, "Accept friend request"),
        h("button", { onclick: drop(null) }, "Decline")];
    case "friends":
      return [h("span", { class: "badge ok" }, "Friends"),
        h("button", { class: "small", onclick: drop(`Stop being friends with ${player.name}?`) }, "Remove friend")];
    default:
      return null;
  }
}
