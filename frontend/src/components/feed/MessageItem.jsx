import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'

export function MessageItem({ message, isLatest, onRetake, isProcessing }) {
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
        <div className="avsm" style={{ background: col, position: 'relative' }}>
          {message.agent_id.substring(0, 2).toUpperCase()}
          {message.emote && (
            <span style={{
              position: 'absolute',
              bottom: -4,
              right: -6,
              fontSize: '12px',
              filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.8))'
            }}>
              {message.emote}
            </span>
          )}
        </div>
        <div className="mbody" style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
            <span className="mname" style={{ color: col, marginBottom: 0 }}>{message.agent_id}</span>
            {message.is_manual && (
              <span style={{
                fontSize: '9px',
                fontWeight: 700,
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                color: '#a5b4fc',
                padding: '1px 5px',
                borderRadius: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }} title="Spoken manually by user">
                ✍️ Manual Line
              </span>
            )}
            {message.is_gossip && (
              <span className="gossip-badge" title={message.gossip_note || "Confidential secret leaked"}>
                🤫 Secret Confided
              </span>
            )}
          </div>
          <div className="mtext">{message.content.replace(/^[^:]+:\s*/, '')}</div>

          {isLatest && !isProcessing && (
            <div style={{ marginTop: '4px' }}>
              <button 
                className="btn-retake" 
                onClick={(e) => { e.stopPropagation(); onRetake?.(); }}
                title="Cut! Re-roll this actor's line..."
              >
                🎲 Retake Line
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  const isDir = message.content?.includes('[DIRECTOR')
  const isGossip = message.content?.includes('[GOSSIP')
  const isSys = message.content?.includes('[SYSTEM') || message.content?.includes('[SCENE START')
  const isScn = message.content?.includes('[SCENE CHANGE')
  const isErr = message.content?.includes('[ERROR')
  
  const className = `msg-a ${isDir ? 'dir' : ''} ${isGossip ? 'gossip-msg' : ''} ${isSys ? 'sys' : ''} ${isScn ? 'scn' : ''} ${isErr ? 'err' : ''}`.trim()
  
  return <div className={className}>{message.content}</div>
}
