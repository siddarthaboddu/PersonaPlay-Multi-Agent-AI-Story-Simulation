/** Canonical agent color palette. */
export const COLORS = [
  '#a78bfa', '#67e8f9', '#f9a8d4', '#fcd34d',
  '#4ade80', '#fc8181', '#fb923c',
]

/** Get color for agent index (wraps around). */
export const agentColor = (index) => COLORS[index % COLORS.length]
