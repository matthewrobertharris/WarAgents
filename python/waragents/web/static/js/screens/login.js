// Signing in and creating an account (#/login). ?next= is where to go afterwards.

import { h, showError } from "../dom.js";
import { signIn } from "../session.js";

export async function mount(root, _params, query) {
  let register = false;
  const name = h("input", { autocomplete: "username", required: true });
  const password = h("input", { type: "password", autocomplete: "current-password", required: true });
  const title = h("h1");
  const submit = h("button", { class: "primary" });
  const hint = h("p", { class: "hint" });
  const toggle = h("button", { type: "button", class: "link-button", onclick: () => { register = !register; render(); } });

  function render() {
    title.textContent = register ? "Create an account" : "Sign in";
    submit.textContent = register ? "Create account" : "Sign in";
    password.autocomplete = register ? "new-password" : "current-password";
    password.minLength = register ? 8 : 0;
    hint.textContent = register
      ? "Your name is how other players see you, and what you sign in with. Passwords need at least 8 characters."
      : "";
    toggle.textContent = register ? "I already have an account" : "New here? Create an account";
  }

  const form = h("form", {
    class: "card login-card",
    onsubmit: async (e) => {
      e.preventDefault();
      submit.disabled = true;
      try {
        await signIn(name.value.trim(), password.value, { register });
        showError("");
        const next = query.get("next");
        location.hash = next && !next.startsWith("#/login") ? next : "#/";
      } catch (err) {
        showError(err.message);
      } finally {
        submit.disabled = false;
      }
    },
  },
  title,
  h("div", { class: "fields" }, h("label", {}, "Name", name), h("label", {}, "Password", password)),
  hint,
  h("div", { class: "login-actions" }, submit, toggle));

  render();
  root.append(
    h("section", { class: "hero" },
      h("h1", {}, "War", h("span", {}, "Agents")),
      h("p", { class: "lede" }, "Teach your agents to think, then send them to war.")),
    form);
  name.focus();
}
