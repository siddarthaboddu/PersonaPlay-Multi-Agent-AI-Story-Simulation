/** Canonical agent color palette with elegant, vibrant artistic hues. */
export const COLORS = [
  '#a78bfa', // Iris / Velvet Violet (Maya)
  '#38bdf8', // Sky Azure / Cyan (Liam)
  '#f472b6', // Radiant Blush / Rose
  '#fbbf24', // Warm Champagne Amber
  '#34d399', // Emerald Mint
  '#fb7185', // Coral Crimson
  '#c084fc', // Orchid Amethyst
]

/** Get color for agent index (wraps around). */
export const agentColor = (index) => COLORS[index % COLORS.length]

