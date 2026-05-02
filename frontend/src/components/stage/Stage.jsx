import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'
import { Avatar } from './Avatar'

export function Stage() {
  const { agents, messages } = useSimulationContext()
  const lastSpk = [...messages].reverse().find(m => m.agent_id)?.agent_id

  return (
    <div className="stage">
      <div className="stage-spotlight"/>
      <div className="slabel">Stage</div>
      {agents.map((ag, i) => (
        <Avatar 
          key={ag.id} 
          agent={ag} 
          index={i} 
          isSpeaking={lastSpk === ag.id}
          color={agentColor(i)}
        />
      ))}
      <div className="stage-floor"/>
    </div>
  )
}
