import { useEffect, useRef } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'
import { MessageItem } from './MessageItem'

export function MessageFeed() {
  const { messages } = useSimulationContext()
  const feedRef = useRef(null)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [messages])

  const visibleMessages = messages.filter(m => {
    if (m.type === 'dialogue' || m.type === 'image') return true
    if (m.content) {
      if (
        m.content.includes('Triggering AI turn') ||
        m.content.includes('already in progress') ||
        m.content.includes('Stage is set') ||
        m.content.includes('Ready — press ▶')
      ) {
        return false
      }
      return true
    }
    return false
  })

  return (
    <div className="feed" ref={feedRef}>
      {visibleMessages.length === 0 ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          color: 'var(--t4)',
          textAlign: 'center',
          gap: 8,
          padding: '24px 16px',
        }}>
          <div style={{ fontSize: 28 }}>🛋️</div>
          <div style={{ fontSize: 13, color: 'var(--t2)', fontWeight: 600 }}>Ready to Begin</div>
          <div style={{ fontSize: 12, maxWidth: 280, lineHeight: 1.5 }}>
            Click <strong>⚡ Next Turn</strong> or enable <strong>🟢 Auto</strong> in the top bar to watch the characters converse.
          </div>
        </div>
      ) : (
        visibleMessages.map((m, i) => (
          <MessageItem key={i} message={m} />
        ))
      )}
    </div>
  )
}

