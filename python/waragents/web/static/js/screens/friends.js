// Friends (#/friends): add a friend by name, answer the requests waiting for you, and see your
// friends. A request only turns into a friendship once the other player accepts it, and until then
// only the two of you see it.

import { get, post } from "../api.js";
import { empty, fill, formatDay, h, showError } from "../dom.js";
import { avatar, friendControls, userChanged } from "../people.js";

export async function mount(root) {
  const body = h("div", { class: "friends-body" });
  const name = h("input", { type: "text", placeholder: "Their player name", "aria-label": "Player name", autocomplete: "off" });
  const note = h("p", { class: "hint", role: "status" });

  async function add(e) {
    e.preventDefault();
    if (!name.value.trim()) return;
    try {
      const sent = await post("/api/friends", { name: name.value });
      note.textContent = sent.friendship === "friends" ? "They'd already asked you, so you're friends now."
        : sent.friendship === "sent" ? "Request sent. They'll appear here once they accept." : "";
      name.value = "";
      await userChanged();
      await render();
    } catch (err) {
      showError(err.message);
    }
  }

  const row = (player, extra) => h("li", { class: "friend-row" },
    h("a", { class: "friend-who", href: `#/players/${player.id}` }, avatar(player),
      h("span", {}, h("strong", {}, player.name),
        h("span", { class: "hint" }, ` Level ${player.level}`, extra ? ` · ${extra}` : ""))),
    h("span", { class: "friend-actions" },
      player.friendship === "friends" && player.ready
        ? h("a", { class: "button small", href: `#/battle?opponent=${player.id}` }, "Fight") : null,
      friendControls(player, render)));

  async function render() {
    const lists = await get("/api/friends");
    const tag = (kind, friendship) => lists[kind].map((p) => ({ ...p, friendship }));
    const received = tag("received", "received");
    const friends = tag("friends", "friends");
    const sent = tag("sent", "sent");
    fill(body,
      received.length ? h("section", { class: "card" },
        h("h2", {}, `Waiting for your answer (${received.length})`),
        h("ul", { class: "plain friend-list" }, received.map((p) => row(p, `asked ${formatDay(p.requested)}`)))) : null,
      h("section", { class: "card" },
        h("h2", {}, `Your friends${friends.length ? ` (${friends.length})` : ""}`),
        friends.length
          ? h("ul", { class: "plain friend-list" }, friends.map((p) => row(p,
            p.ready ? `friends since ${formatDay(p.since)}` : "no default tree yet, so they can't be picked to fight")))
          : empty("No friends yet. Add someone by their player name above, or from their profile.")),
      sent.length ? h("section", { class: "card" },
        h("h2", {}, "Waiting for them"),
        h("ul", { class: "plain friend-list" }, sent.map((p) => row(p, `asked ${formatDay(p.requested)}`)))) : null);
  }

  root.append(
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Friends"),
      h("p", { class: "hint" }, "Players you've both agreed to be friends with. Ask someone by their player name, ",
        "or with Add friend on their profile. They show up here once they accept."))),
    h("section", { class: "card" },
      h("h2", {}, "Add a friend"),
      h("form", { class: "inline-form", onsubmit: add }, name, h("button", { class: "primary", type: "submit" }, "Send request")),
      note),
    body);
  await render();
}
