import { useSimulationContext } from '../../context/useSimulationContext'
import { agentColor } from '../../utils/colors'

// Helper to format parenthetical micro-actions in dialogue like a professional screenplay
function formatDialogueContent(rawText) {
  const content = rawText.replace(/^[^:]+:\s*/, '')
  // Split by parentheticals like (smirks softly) or *(takes a sip)* or *laughs*
  const parts = content.split(/(\([^)]{2,80}\)|\*[^*]{2,80}\*)/g)
  return parts.map((part, idx) => {
    if ((part.startsWith('(') && part.endsWith(')')) || (part.startsWith('*') && part.endsWith('*'))) {
      const cleanPart = part.replace(/^\*+|\*+$/g, '')
      return (
        <span key={idx} className="micro-action" style={{
          fontStyle: 'italic',
          color: 'var(--t3)',
          margin: '0 2px',
          fontWeight: 400,
          background: 'rgba(255, 255, 255, 0.03)',
          padding: '1px 5px',
          borderRadius: '4px'
        }}>
          {cleanPart.startsWith('(') ? cleanPart : `(${cleanPart})`}
        </span>
      )
    }
    return part
  })
}

export function MessageItem({ message, isLatest, onRetake, isProcessing }) {
  const { agents } = useSimulationContext()

  if (message.type === 'image') {
    return (
      <div style={{
        animation: 'messageSlideIn 0.3s ease-out',
        background: 'var(--s2)',
        padding: '10px',
        borderRadius: '12px',
        border: '1px solid var(--border)'
      }}>
        <div style={{
          fontSize: 11,
          color: 'var(--gold)',
          marginBottom: 8,
          fontStyle: 'italic',
          display: 'flex',
          alignItems: 'center',
          gap: 6
        }}>
          <span>🎬 Scene Visualization:</span>
          <span style={{ color: 'var(--t3)' }}>"{message.prompt?.substring(0, 80)}…"</span>
        </div>
        <img 
          src={message.url} alt="" 
          style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border)', display: 'block' }}
        />
      </div>
    )
  }

  if (message.type === 'dialogue' && message.agent_id) {
    const idx = agents.findIndex(a => a.id === message.agent_id)
    const col = agentColor(idx >= 0 ? idx : 0)
    return (
      <div className="msg-d" style={{ borderLeftColor: col }}>
        <div className="avsm" style={{ background: col, position: 'relative' }}>
          {message.agent_id.substring(0, 2).toUpperCase()}
          {message.emote && (
            <span style={{
              position: 'absolute',
              bottom: -5,
              right: -7,
              fontSize: '13px',
              filter: 'drop-shadow(0 2px 5px rgba(0,0,0,0.8))'
            }}>
              {message.emote}
            </span>
          )}
        </div>
        <div className="mbody" style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
            <span className="mname" style={{ color: col }}>{message.agent_id}</span>
            {message.is_manual && (
              <span style={{
                fontSize: '9.5px',
                fontWeight: 800,
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                color: '#38bdf8',
                padding: '2px 7px',
                borderRadius: '999px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }} title="Spoken directly by user in roleplay">
                <span>✍️</span> Direct Roleplay
              </span>
            )}
            {message.is_gossip && (
              <span className="gossip-badge" title={message.gossip_note || "Confidential secret leaked"}>
                <span>🤫</span> Secret Confided
              </span>
            )}
          </div>
          <div className="mtext">
            {formatDialogueContent(message.content)}
          </div>

          {isLatest && !isProcessing && (
            <div style={{ marginTop: '6px' }}>
              <button 
                className="btn-retake" 
                onClick={(e) => { e.stopPropagation(); onRetake?.(); }}
                title="Cut! Re-roll this character's line with an alternate response"
              >
                <span>🎲</span> Retake Line
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Cinematic cue cards for director plot twists, scene shifts, and gossip notes
  const isDir = message.content?.includes('[DIRECTOR')
  const isGossip = message.content?.includes('[GOSSIP')
  const isScn = message.content?.includes('[SCENE CHANGE')
  // The backend surfaces failures two ways: as an `action` line whose content is
  // prefixed "[ERROR]:", and as a dedicated `{"type": "error"}` payload. Match
  // both, otherwise failures render as ordinary system text.
  const isErr = message.type === 'error' || /\[ERROR\]/.test(message.content ?? '')
  
  if (isDir) {
    const text = message.content.replace(/^\[DIRECTOR[^\]]*\]:\s*/, '')
    return (
      <div className="msg-a dir" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: 14 }}>🎬</span>
        <div>
          <span style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.85, display: 'block' }}>
            Director Intervention
          </span>
          <span>{text}</span>
        </div>
      </div>
    )
  }

  if (isScn) {
    const text = message.content.replace(/^\[SCENE CHANGE[^\]]*\]:\s*/, '')
    return (
      <div className="msg-a scn" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: 14 }}>📍</span>
        <div>
          <span style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.85, display: 'block' }}>
            Stage Shift
          </span>
          <span>{text}</span>
        </div>
      </div>
    )
  }

  if (isGossip) {
    const text = message.content.replace(/^\[GOSSIP[^\]]*\]:\s*/, '')
    return (
      <div className="msg-a gossip-msg" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: 14 }}>🤫</span>
        <div>
          <span style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.85, display: 'block' }}>
            Secret Diffusion
          </span>
          <span>{text}</span>
        </div>
      </div>
    )
  }

  const className = `msg-a ${isErr ? 'err' : 'sys'}`.trim()
  return <div className={className}>{message.content}</div>
}

