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

  // Default fallback so bar is always visible even prior to WS connection
  const effectiveAgents = (agents && agents.length > 0)
    ? agents
    : [{ id: 'Maya' }, { id: 'Liam' }]

  // Default to first agent if none selected or agent list changes
  useEffect(() => {
    if (effectiveAgents.length > 0) {
      if (!selectedAgentId || !effectiveAgents.some(a => a.id === selectedAgentId)) {
        setSelectedAgentId(effectiveAgents[0].id)
      }
    }
  }, [effectiveAgents, selectedAgentId])

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

  const selectedIdx = effectiveAgents.findIndex(a => a.id === selectedAgentId)
  const currentColor = agentColor(selectedIdx >= 0 ? selectedIdx : 0)

  return (
    <div style={{
      borderTop: '1px solid var(--border)',
      background: 'rgba(10, 13, 24, 0.88)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      padding: '11px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '9px',
      flexShrink: 0,
      boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.4)',
    }}>
      {/* Top bar: Character selector pills & Pause/Auto + AI Response toggle */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto', paddingBottom: '2px' }}>
          <span style={{ fontSize: '10.5px', fontWeight: 800, color: 'var(--t4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Speak as:
          </span>
          {effectiveAgents.map((a, idx) => {
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
                  gap: '6px',
                  padding: '4px 10px',
                  borderRadius: 'var(--r-pill)',
                  fontSize: '11.5px',
                  fontWeight: isSelected ? 800 : 500,
                  border: `1px solid ${isSelected ? color : 'var(--border)'}`,
                  background: isSelected ? `${color}25` : 'rgba(255, 255, 255, 0.03)',
                  color: isSelected ? '#ffffff' : 'var(--t3)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isSelected ? `0 0 12px ${color}40` : 'none',
                }}
              >
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: color,
                  boxShadow: isSelected ? `0 0 8px ${color}` : 'none',
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
                gap: '5px',
                padding: '3px 9px',
                borderRadius: '6px',
                fontSize: '10.5px',
                fontWeight: 800,
                border: '1px solid rgba(245, 208, 97, 0.45)',
                background: 'rgba(245, 208, 97, 0.15)',
                color: 'var(--gold)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              title="Pause auto mode to write dialogue"
            >
              <span>⏸ Pause Auto</span>
            </button>
          ) : (
            <span style={{
              fontSize: '10px',
              color: '#38bdf8',
              background: 'rgba(56, 189, 248, 0.12)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              padding: '2px 8px',
              borderRadius: 'var(--r-pill)',
              fontWeight: 800,
              letterSpacing: '0.04em'
            }}>
              ⏸ Paused
            </span>
          )}

          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--t3)',
            cursor: 'pointer',
            userSelect: 'none',
            whiteSpace: 'nowrap',
          }} title="When checked, the other character will immediately generate a spoken reply and remain paused">
            <input
              type="checkbox"
              checked={triggerResponse}
              onChange={(e) => setTriggerResponse(e.target.checked)}
              style={{ width: '13px', height: '13px', cursor: 'pointer', accentColor: 'var(--purple)' }}
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
                ? "Characters conversing…" 
                : auto
                ? `Auto running (click to pause & speak as ${selectedAgentId || 'character'})…`
                : `Say something as ${selectedAgentId || 'character'}… (Press Enter to speak)`
            }
            style={{
              paddingLeft: '14px',
              paddingRight: '14px',
              paddingTop: '9px',
              paddingBottom: '9px',
              fontSize: '13px',
              borderRadius: '10px',
              background: 'rgba(5, 7, 15, 0.7)',
              border: `1px solid ${selectedAgentId ? `${currentColor}60` : 'var(--border)'}`,
              color: 'var(--t1)',
              boxShadow: selectedAgentId ? `0 0 14px ${currentColor}15` : 'none',
            }}
          />
        </div>

        {auto && (
          <button
            type="button"
            onClick={pause}
            style={{
              padding: '8px 12px',
              fontSize: '11.5px',
              fontWeight: 700,
              borderRadius: '9px',
              border: '1px solid rgba(245, 208, 97, 0.4)',
              background: 'rgba(245, 208, 97, 0.15)',
              color: 'var(--gold)',
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
            padding: '9px 16px',
            fontSize: '12px',
            fontFamily: 'var(--font-sans)',
            fontWeight: 800,
            borderRadius: '9px',
            border: 'none',
            background: text.trim() && !isProcessing
              ? `linear-gradient(135deg, ${currentColor}, #6366f1)`
              : 'rgba(255, 255, 255, 0.05)',
            color: text.trim() && !isProcessing ? '#050711' : 'var(--t4)',
            cursor: text.trim() && !isProcessing ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            whiteSpace: 'nowrap',
            transition: 'all 0.15s ease',
            boxShadow: text.trim() && !isProcessing ? `0 0 16px ${currentColor}40` : 'none',
          }}
        >
          <span>🗣️</span>
          <span>Speak</span>
          <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 2, fontFamily: 'var(--font-mono)' }}>↵</span>
        </button>
      </form>
    </div>
  )
}
