// Calls to the Flask API. Errors become exceptions with the server's message, and `problems`
// when the server lists them.

export async function api(path, { method = "GET", body } = {}) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data.detail || res.statusText);
    error.problems = data.problems ?? [];
    throw error;
  }
  return data;
}

export const get = (path) => api(path);
export const post = (path, body = {}) => api(path, { method: "POST", body });
export const put = (path, body) => api(path, { method: "PUT", body });
export const remove = (path) => api(path, { method: "DELETE" });

// What can go in maps, trees and games. It never changes while the server runs, so fetch it once.
let referencePromise = null;
export function reference() {
  referencePromise ??= get("/api/reference");
  return referencePromise;
}
