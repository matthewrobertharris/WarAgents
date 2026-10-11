// Team colours. A team's own colour wins; otherwise teams named after a colour get it, and the
// rest take the next palette entry.

const NAMED_COLOURS = {
  red: "#e03131", green: "#2f9e44", blue: "#1c7ed6", yellow: "#f08c00",
  orange: "#e8590c", purple: "#9c36b5", pink: "#d6336c", teal: "#0ca678",
};
export const PALETTE = ["#1c7ed6", "#e8590c", "#9c36b5", "#0ca678", "#f08c00", "#d6336c", "#495057"];

export function teamColour(players, name) {
  const index = players.findIndex((p) => p.name === name);
  const player = players[index];
  if (player?.colour) return player.colour;
  return NAMED_COLOURS[name.toLowerCase()] ?? PALETTE[Math.max(0, index) % PALETTE.length];
}

// The colour for a map's start slot before any team is in it.
export const slotColour = (slot) => PALETTE[(slot - 1) % PALETTE.length];
