// Draws a map or a running game onto a canvas. Used by the game view and the map previews.
//
// data has width, height, dirt and food (rows by y, with null for a hole) and plants. It can also
// have agents (a running game) or starts (a map's start slots). Row y = 0 is drawn at the bottom.

import { slotColour } from "./colours.js";

const LOW = [233, 223, 201];
const HIGH = [138, 98, 64];

function mix(a, b, t) {
  return a.map((v, i) => Math.round(v + (b[i] - v) * t));
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// Returns the tile size used, in CSS pixels.
export function drawBoard(canvas, data, options = {}) {
  const { minTile = 14, maxTile = 48, selected = null, colourOf = () => "#495057" } = options;
  const available = options.maxWidth ?? (canvas.parentElement?.clientWidth || 600);
  const size = Math.max(minTile, Math.min(maxTile, Math.floor(available / data.width)));
  const dpr = window.devicePixelRatio || 1;
  canvas.width = data.width * size * dpr;
  canvas.height = data.height * size * dpr;
  canvas.style.width = `${data.width * size}px`;
  canvas.style.height = `${data.height * size}px`;

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, data.width * size, data.height * size);
  const heights = data.dirt.flat().filter((d) => d !== null);
  const maxDirt = Math.max(4, ...heights);
  const py = (y) => (data.height - 1 - y) * size;

  for (let y = 0; y < data.height; y++) {
    for (let x = 0; x < data.width; x++) {
      const dirt = data.dirt[y][x];
      if (dirt === null) continue;  // a hole: leave the background showing
      const [r, g, b] = mix(LOW, HIGH, dirt / maxDirt);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(x * size, py(y), size, size);
      const food = data.food[y][x];
      if (food > 0) {
        ctx.fillStyle = `rgba(116,184,22,${Math.min(0.7, 0.12 + food / 60)})`;
        ctx.fillRect(x * size, py(y), size, size);
      }
      ctx.strokeStyle = "rgba(0,0,0,0.07)";
      ctx.strokeRect(x * size + 0.5, py(y) + 0.5, size - 1, size - 1);
    }
  }

  for (const plant of data.plants) {
    const cx = plant.x * size + size * 0.78;
    const cy = py(plant.y) + size * 0.22;
    ctx.fillStyle = "#2b8a3e";
    ctx.beginPath();
    ctx.arc(cx, cy, Math.max(2, size * 0.15), 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#b2f2bb";
    ctx.beginPath();
    ctx.arc(cx, cy, Math.max(1, size * 0.06), 0, Math.PI * 2);
    ctx.fill();
  }

  for (const start of data.starts ?? []) {
    const cx = start.x * size + size / 2;
    const cy = py(start.y) + size / 2;
    ctx.lineWidth = Math.max(1.5, size * 0.08);
    ctx.strokeStyle = slotColour(start.slot);
    ctx.fillStyle = "rgba(255,255,255,0.75)";
    ctx.beginPath();
    ctx.arc(cx, cy, size * 0.34, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    if (size >= 14) {
      ctx.fillStyle = slotColour(start.slot);
      ctx.font = `700 ${Math.round(size * 0.42)}px system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(start.slot), cx, cy + 1);
    }
  }

  for (const agent of data.agents ?? []) {
    const colour = colourOf(agent);
    const cx = agent.x * size + size / 2;
    const cy = py(agent.y) + size / 2;
    const r = size * 0.36;
    const ring = Math.max(2, size * 0.09);
    ctx.fillStyle = colour;
    ctx.beginPath();
    ctx.arc(cx, cy, r - ring, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = ring;
    ctx.strokeStyle = "rgba(0,0,0,0.18)";
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = colour;
    ctx.beginPath();
    const health = Math.max(0, agent.health) / agent.maxHealth;
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * health);
    ctx.stroke();
    if (agent.dirt || agent.food) {
      ctx.fillStyle = agent.food ? "#d8f5a2" : "#5c3d1e";
      const d = size * 0.14;
      ctx.fillRect(cx - d / 2, cy - d / 2, d, d);
    }
    if (agent.id === selected) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = cssVar("--ink");
      ctx.beginPath();
      ctx.arc(cx, cy, r + ring, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
  return size;
}

// The tile under a mouse event, or null if it's off the grid or a hole.
export function tileAt(canvas, data, size, event) {
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor((event.clientX - rect.left) / size);
  const y = data.height - 1 - Math.floor((event.clientY - rect.top) / size);
  if (x < 0 || y < 0 || x >= data.width || y >= data.height || data.dirt[y][x] === null) return null;
  return { x, y };
}

// A small preview of a catalogue map, for lists.
export function mapPreview(map, maxWidth = 220, maxTile = 16) {
  const canvas = document.createElement("canvas");
  canvas.className = "preview";
  drawBoard(canvas, map, { maxWidth, minTile: 3, maxTile });
  return canvas;
}
