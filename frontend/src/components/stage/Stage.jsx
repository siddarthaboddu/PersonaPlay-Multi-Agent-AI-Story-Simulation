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

  return (
    <div className={`stage ${tensionClass}`}>
      <div className="stage-spotlight"/>
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
