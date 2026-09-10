export function Avatar({ agent, index, isSpeaking, color, total }) {
  // Semi-circle theater layout (centered if solo actor)
  const angle = total <= 1 ? 0 : (index / (total - 1)) * 120 - 60 // -60 to 60 degrees
  const radius = 35 // distance from center
  
  const left = 50 + radius * Math.sin((angle * Math.PI) / 180)
  const top = 50 - radius * Math.cos((angle * Math.PI) / 180) + 15

  // Derive expressive emote based on state, secrets, or emotions
  let emote = agent.last_emote
  let emoteTitle = "Mood: Calm"

  if (isSpeaking && agent.last_emote) {
    emote = agent.last_emote
    emoteTitle = `Reaction: ${agent.last_emote}`
  } else if (agent.pending_whisper) {
    emote = "🤫"
    emoteTitle = "Holding a secret whisper from Director"
  } else if (agent.known_secrets && agent.known_secrets.length > 0) {
    emote = "🤫"
    emoteTitle = `Holding ${agent.known_secrets.length} secret(s)`
  } else if (agent.emotions?.tension > 0.65) {
    emote = "⚡"
    emoteTitle = "High Tension / Agitated"
  } else if (agent.emotions?.affection > 0.65) {
    emote = "💖"
    emoteTitle = "Fond / Affectionate"
  } else if (agent.emotions?.suspicion > 0.60) {
    emote = "❓"
    emoteTitle = "Suspicious / Alert"
  } else if (agent.emotions?.energy < 0.35) {
    emote = "🥱"
    emoteTitle = "Low Energy / Weary"
  } else {
    emote = isSpeaking ? "💬" : "☕"
    emoteTitle = isSpeaking ? "Speaking" : "Relaxed"
  }

  return (
    <div 
      className={`avatar ${isSpeaking ? 'speaking' : ''}`}
      style={{ left: `${left}%`, top: `${top}%`, background: color }}
      title={`${agent.id} — ${emoteTitle}`}
    >
      <div 
        className={`avatar-emote ${isSpeaking ? 'speaking-emote' : ''}`} 
        title={emoteTitle}
      >
        {emote}
      </div>
      {agent.id.substring(0, 2).toUpperCase()}
      <span className="atag">{agent.id}</span>
    </div>
  )
}
