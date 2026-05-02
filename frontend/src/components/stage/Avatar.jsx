export function Avatar({ agent, index, isSpeaking, color, total }) {
  // Semi-circle theater layout
  const angle = (index / (total - 1 || 1)) * 120 - 60 // -60 to 60 degrees
  const radius = 35 // distance from center
  
  const left = 50 + radius * Math.sin((angle * Math.PI) / 180)
  const top = 50 - radius * Math.cos((angle * Math.PI) / 180) + 15

  return (
    <div 
      className={`avatar ${isSpeaking ? 'speaking' : ''}`}
      style={{ left: `${left}%`, top: `${top}%`, background: color }}
    >
      {agent.id.substring(0, 2).toUpperCase()}
      <span className="atag">{agent.id}</span>
    </div>
  )
}
