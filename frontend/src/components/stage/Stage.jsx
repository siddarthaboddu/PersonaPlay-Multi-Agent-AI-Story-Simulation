import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'
import { Avatar } from './Avatar'

export function Stage() {
  const { agents, messages, vitals } = useSimulationContext()
  const lastSpk = [...messages].reverse().find(m => m.agent_id)?.agent_id
  const tension = vitals?.tension ?? 0.5

  const tensionClass = tension >= 0.72 
    ? 'stage-tension-high' 
    : tension >= 0.42 
      ? 'stage-tension-med' 
      : 'stage-tension-low'

  const tensionLabel = tension >= 0.72 
    ? '🔥 High Tension' 
    : tension >= 0.42 
      ? '⚡ Rising Energy' 
      : '✨ Calm Atmosphere'

  return (
    <div className={`stage ${tensionClass}`}>
      <div className="stage-spotlight"/>
      <div style={{
        position: 'absolute',
        top: 8,
        right: 12,
        fontSize: 10,
        fontWeight: 700,
        fontFamily: 'var(--font-sans)',
        letterSpacing: '0.04em',
        padding: '2px 8px',
        borderRadius: '999px',
        background: 'rgba(0, 0, 0, 0.45)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        color: tension >= 0.72 ? 'var(--red)' : tension >= 0.42 ? 'var(--gold)' : 'var(--cyan)',
        backdropFilter: 'blur(8px)',
        zIndex: 4,
        pointerEvents: 'none',
        userSelect: 'none'
      }}>
        {tensionLabel}
      </div>
      {agents.map((ag, i) => (
        <Avatar 
          key={ag.id} 
          agent={ag} 
          index={i} 
          total={agents.length}
          isSpeaking={lastSpk === ag.id}
          color={agentColor(i)}
        />
      ))}
      <div className="stage-floor"/>
    </div>
  )
}
