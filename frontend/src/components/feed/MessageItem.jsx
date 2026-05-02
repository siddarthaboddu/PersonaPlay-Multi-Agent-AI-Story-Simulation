import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'

export function MessageItem({ message }) {
  const { agents } = useSimulationContext()

  if (message.type === 'image') {
    return (
      <div style={{ animation: 'up .3s ease-out' }}>
        <div style={{ fontSize: 11, color: 'var(--t4)', marginBottom: 6, fontStyle: 'italic' }}>
          🎬 {message.prompt?.substring(0, 90)}…
        </div>
        <img 
          src={message.url} alt="" 
          style={{ width: '100%', borderRadius: 10, border: '1px solid var(--border)' }}
        />
      </div>
    )
  }

  if (message.type === 'dialogue' && message.agent_id) {
    const idx = agents.findIndex(a => a.id === message.agent_id)
    const col = agentColor(idx >= 0 ? idx : 0)
    return (
      <div className="msg-d">
        <div className="avsm" style={{ background: col }}>
          {message.agent_id.substring(0, 2).toUpperCase()}
        </div>
        <div className="mbody">
          <div className="mname" style={{ color: col }}>{message.agent_id}</div>
          <div className="mtext">{message.content.replace(/^[^:]+:\s*/, '')}</div>
        </div>
      </div>
    )
  }

  const isDir = message.content?.includes('[DIRECTOR')
  const isSys = message.content?.includes('[SYSTEM') || message.content?.includes('[SCENE START')
  const isScn = message.content?.includes('[SCENE CHANGE')
  const isErr = message.content?.includes('[ERROR')
  
  const className = `msg-a ${isDir ? 'dir' : ''} ${isSys ? 'sys' : ''} ${isScn ? 'scn' : ''} ${isErr ? 'err' : ''}`.trim()
  
  return <div className={className}>{message.content}</div>
}
