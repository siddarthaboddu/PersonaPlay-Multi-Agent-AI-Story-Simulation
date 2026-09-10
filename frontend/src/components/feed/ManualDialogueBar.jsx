import { useState, useEffect } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'

export function ManualDialogueBar() {
  const { 
    agents, sendManualDialogue, isProcessing, 
    auto, setAuto, pause 
  } = useSimulationContext()
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [text, setText] = useState('')
  const [triggerResponse, setTriggerResponse] = useState(true)

  // Default to first agent if none selected or agent list changes
  useEffect(() => {
    if (agents && agents.length > 0) {
      if (!selectedAgentId || !agents.some(a => a.id === selectedAgentId)) {
        setSelectedAgentId(agents[0].id)
      }
    }
  }, [agents, selectedAgentId])

  const handleFocus = () => {
    // Automatically pause auto mode when user focuses the dialogue box to type
    if (auto) {
      pause()
    }
  }

  const handleSubmit = (e) => {
    e?.preventDefault()
    const content = text.trim()
    if (!content || !selectedAgentId || isProcessing) return

    sendManualDialogue(selectedAgentId, content, triggerResponse)
    setText('')
  }

  if (!agents || agents.length === 0) return null

  const selectedIdx = agents.findIndex(a => a.id === selectedAgentId)
  const currentColor = agentColor(selectedIdx >= 0 ? selectedIdx : 0)

  return (
    <div style={{
      borderTop: '1px solid var(--border)',
      background: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(10px)',
      padding: '10px 14px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      flexShrink: 0,
    }}>
      {/* Top bar: Character selector pills & Pause/Auto + AI Response toggle */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto', paddingBottom: '2px' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--t4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Speak as:
          </span>
          {agents.map((a, idx) => {
            const isSelected = a.id === selectedAgentId
            const color = agentColor(idx)
            return (
              <button
                key={a.id}
                type="button"
                onClick={() => setSelectedAgentId(a.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '3px 9px',
                  borderRadius: '16px',
                  fontSize: '11px',
                  fontWeight: isSelected ? 800 : 500,
                  border: `1px solid ${isSelected ? color : 'rgba(255,255,255,0.08)'}`,
                  background: isSelected ? `${color}25` : 'rgba(0,0,0,0.25)',
                  color: isSelected ? '#ffffff' : 'var(--t3)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isSelected ? `0 0 10px ${color}33` : 'none',
                }}
              >
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: color,
                  boxShadow: isSelected ? `0 0 6px ${color}` : 'none',
                }} />
                {a.id}
              </button>
            )
          })}
        </div>

        {/* Right side controls: Pause/Resume + AI Reply */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {auto ? (
            <button
              type="button"
              onClick={pause}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '10px',
                fontWeight: 800,
                border: '1px solid rgba(245, 166, 35, 0.4)',
                background: 'rgba(245, 166, 35, 0.2)',
                color: 'var(--amber)',
                cursor: 'pointer',
                animation: 'pulseGlow 2s infinite ease-in-out',
              }}
              title="Pause auto mode to take your time writing dialogue"
            >
              <span>⏸ Pause Auto</span>
            </button>
          ) : (
            <span style={{
              fontSize: '10px',
              color: '#38bdf8',
              background: 'rgba(56,189,248,0.1)',
              border: '1px solid rgba(56,189,248,0.25)',
              padding: '2px 7px',
              borderRadius: '4px',
              fontWeight: 700,
            }}>
              ⏸ Paused
            </span>
          )}

          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '10px',
            color: 'var(--t3)',
            cursor: 'pointer',
            userSelect: 'none',
            whiteSpace: 'nowrap',
          }} title="When checked, the other character will immediately generate a spoken reply and remain paused">
            <input
              type="checkbox"
              checked={triggerResponse}
              onChange={(e) => setTriggerResponse(e.target.checked)}
              style={{ width: '12px', height: '12px', cursor: 'pointer', accentColor: 'var(--purple)' }}
            />
            <span>AI Reply</span>
          </label>
        </div>
      </div>

      {/* Input row */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, display: 'flex', alignItems: 'center' }}>
          <input
            type="text"
            value={text}
            onFocus={handleFocus}
            onChange={(e) => setText(e.target.value)}
            disabled={isProcessing}
            placeholder={
              isProcessing 
                ? "Characters conversing..." 
                : auto
                ? `Auto running (click to pause & speak as ${selectedAgentId || 'character'})...`
                : `Type dialogue for ${selectedAgentId || 'character'}... (Enter to speak)`
            }
            style={{
              paddingLeft: '12px',
              paddingRight: '12px',
              paddingTop: '8px',
              paddingBottom: '8px',
              fontSize: '12px',
              borderRadius: '8px',
              background: 'rgba(0,0,0,0.4)',
              border: `1px solid ${selectedAgentId ? `${currentColor}40` : 'var(--bhi)'}`,
              color: 'var(--t1)',
            }}
          />
        </div>

        {auto && (
          <button
            type="button"
            onClick={pause}
            style={{
              padding: '8px 12px',
              fontSize: '11px',
              fontWeight: 700,
              borderRadius: '8px',
              border: '1px solid rgba(245, 166, 35, 0.4)',
              background: 'rgba(245, 166, 35, 0.15)',
              color: 'var(--amber)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
            title="Pause auto play so you can manually enter character lines"
          >
            ⏸ Pause
          </button>
        )}

        <button
          type="submit"
          disabled={!text.trim() || isProcessing}
          style={{
            padding: '8px 14px',
            fontSize: '12px',
            fontWeight: 700,
            borderRadius: '8px',
            border: 'none',
            background: text.trim() && !isProcessing
              ? `linear-gradient(135deg, ${currentColor}, #6366f1)`
              : 'rgba(255,255,255,0.06)',
            color: text.trim() && !isProcessing ? '#000' : 'var(--t4)',
            cursor: text.trim() && !isProcessing ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease',
          }}
        >
          <span>🗣️</span>
          <span>Speak</span>
        </button>
      </form>
    </div>
  )
}
