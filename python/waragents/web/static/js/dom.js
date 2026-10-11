// Small DOM helpers shared by every screen.

export const $ = (id) => document.getElementById(id);

// h("button", { class: "primary", onclick: save }, "Save") builds an element. Children can be
// strings, numbers, nodes or arrays of them; null, undefined and false are skipped. Props that the
// element has as a property (value, checked, disabled, ...) are set as properties, after the
// children, so a <select>'s value can pick one of its options.
export function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "class") node.className = value;
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  return node;
}

// Like node.replaceChildren(), but skips null, undefined and false the way h() does, rather
// than showing them as text.
export function fill(node, ...children) {
  node.replaceChildren(...children.flat(Infinity).filter((c) => c !== null && c !== undefined && c !== false));
  return node;
}

export function showError(message) {
  $("error-text").textContent = message ?? "";
  $("error").hidden = !message;
}

$("error-close").addEventListener("click", () => showError(""));

export function formatDate(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

// A date without the time, such as "3 Oct 2026".
export function formatDay(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

// An empty-state paragraph.
export const empty = (text) => h("p", { class: "empty" }, text);
