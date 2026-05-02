/**
 * Narrative beat map — mirrors backend app/agents/beats.py.
 *
 * IMPORTANT: This is the frontend cache of the beat data.
 * The app fetches the authoritative version from GET /api/beats on mount
 * and overwrites this fallback. Do not edit this array manually —
 * edit the Python source and let the API sync it.
 */
export const BEATS = [
  [0,   3,   'COLD OPEN'],
  [4,   7,   'STATUS QUO'],
  [8,   12,  'FIRST FRICTION'],
  [13,  18,  'ESCALATION'],
  [19,  25,  'COMPLICATION'],
  [26,  32,  'CONFRONTATION'],
  [33,  40,  'REVELATION'],
  [41,  48,  'POWER SHIFT'],
  [49,  58,  'CRISIS POINT'],
  [59,  68,  'CLIMAX I'],
  [69,  80,  'CLIMAX II'],
  [81,  92,  'BREAKING POINT'],
  [93,  105, 'FALLING ACTION'],
  [106, 120, 'RECKONING'],
  [121, 135, 'UNEASY PEACE'],
  [136, 155, 'NEW COMPLICATION'],
  [156, 175, 'SECOND ARC'],
  [176, 200, 'SECOND CLIMAX'],
  [201, 999, 'EPILOGUE'],
]

/** Find the beat tuple [start, end, label] for a given turn. */
export const getBeat = (turn) =>
  BEATS.find(([s, e]) => turn >= s && turn <= e) ?? BEATS[BEATS.length - 1]

/** Progress within the current beat (0–1). */
export const getBeatProgress = (turn) => {
  const [s, e] = getBeat(turn)
  return Math.min(1, (turn - s) / (e - s + 1))
}
