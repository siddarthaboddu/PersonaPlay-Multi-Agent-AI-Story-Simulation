export function Avatar({ agent, index, isSpeaking, color }) {
  const left = 18 + ((index * 45) % 58) + (agent.emotions?.energy ?? 0.5) * 12
  const top = 22 + ((index * 22) % 34) + (agent.emotions?.tension ?? 0.5) * 14

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
