/** Reusable toggle switch component. */
export function Toggle({ label, checked, onChange, icon }) {
  return (
    <div className="togrow">
      <span className="togl">{icon} {label}</span>
      <label className="sw">
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className="sw-t" />
      </label>
    </div>
  )
}
