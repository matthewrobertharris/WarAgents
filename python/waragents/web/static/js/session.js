// Who's signed in. The router loads this before showing any screen, and the sign-in screen
// updates it.

import { get, post } from "./api.js";

let current; // undefined until loaded, then the player or null

export async function loadUser() {
  current = await get("/api/auth/me");
  return current;
}

// The signed-in player ({id, name, colour, startTree, admin, ...}) or null.
export const user = () => current ?? null;
export const isAdmin = () => Boolean(current?.admin);

export async function signIn(name, password, { register = false } = {}) {
  current = await post(register ? "/api/auth/register" : "/api/auth/login", { name, password });
  return current;
}

export async function signOut() {
  await post("/api/auth/logout");
  current = null;
}

// Call after changing your own profile, so the header shows the new name and colour.
export function updateUser(changes) {
  if (current) current = { ...current, ...changes };
}
