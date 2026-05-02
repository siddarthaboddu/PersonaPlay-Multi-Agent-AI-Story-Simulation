/** Model connection test status badge. */
export function Badge({ id, results }) {
  const s = results[id]
  if (!s)                   return <span className="badge idle">Idle</span>
  if (s.status === 'loading') return <span className="badge load">Testing…</span>
  if (s.status === 'ok')      return <span className="badge ok">✓ Live</span>
  return <span className="badge err">✗ Error</span>
}
