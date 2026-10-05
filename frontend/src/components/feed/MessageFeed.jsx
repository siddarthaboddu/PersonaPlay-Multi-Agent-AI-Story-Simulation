import { useEffect, useRef } from 'react'
import { useSimulationContext } from '../../context/useSimulationContext'
import { MessageItem } from './MessageItem'

export function MessageFeed() {
  const { messages, retakeTurn, isProcessing } = useSimulationContext()
  const feedRef = useRef(null)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [messages])

  const visibleMessages = messages.filter(m => {
    if (m.type === 'dialogue') return true
    if (m.content) {
      if (
        m.content.includes('Triggering AI turn') ||
        m.content.includes('Stage is set') ||
        m.content.includes('Ready — press ▶')
      ) {
        return false
      }
      return true
    }
    return false
  })

  const lastDialogueIdx = visibleMessages.map(m => m.type).lastIndexOf('dialogue')

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
          gap: 12,
          padding: '32px 20px',
        }}>
          <div style={{
            width: 54,
            height: 54,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, rgba(245,208,97,0.18), rgba(167,139,250,0.18))',
            border: '1px solid rgba(245,208,97,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 26,
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
          }}>
            🎭
          </div>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 17, color: 'var(--t1)', fontWeight: 700, letterSpacing: '-0.2px' }}>
            The Stage is Set
          </div>
          <div style={{ fontSize: 13, color: 'var(--t3)', maxWidth: 320, lineHeight: 1.6 }}>
            The characters are in the room. Press <strong style={{ color: 'var(--gold)' }}>⚡ Next Turn</strong>, activate <strong style={{ color: 'var(--green)' }}>🟢 Auto</strong>, or speak as a character below.
          </div>
        </div>
      ) : (
        visibleMessages.map((m, i) => (
          <MessageItem 
            key={i} 
            message={m} 
            isLatest={i === lastDialogueIdx} 
            onRetake={retakeTurn}
            isProcessing={isProcessing}
          />
        ))
      )}
    </div>
  )
}

