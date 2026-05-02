import { useSimulationContext } from '../../context/SimulationContext'
import { Stage } from '../stage/Stage'
import { MessageFeed } from '../feed/MessageFeed'

export function TheaterPanel() {
  const { world } = useSimulationContext()

  return (
    <div className="panel">
      <div className="ph">
        <div className="ph-icon" style={{ background: 'rgba(103,232,249,.12)' }}>🎭</div>
        <span className="ph-title">Theater</span>
        <span className="ph-sub">{world.location}</span>
      </div>

      <Stage />
      <MessageFeed />
    </div>
  )
}
