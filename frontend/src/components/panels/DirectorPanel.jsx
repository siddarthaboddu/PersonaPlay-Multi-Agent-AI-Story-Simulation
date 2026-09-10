import { useState } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'

export function DirectorPanel() {
  const { 
    world, vitals, agents, injectChaos, whisperDirective, sendManualDialogue,
    auto, autoDelay, setAutoPacing, autoCountdown, isProcessing,
    phasesEnabled, togglePhases
  } = useSimulationContext()

  const [target, setTarget] = useState('world')
  const [directiveText, setDirectiveText] = useState('')

  const handleDirect = (e) => {
    e.preventDefault()
    const text = directiveText.trim()
    if (!text) return

    if (target.startsWith('speak_')) {
      const agentId = target.replace('speak_', '')
      sendManualDialogue(agentId, text, true)
    } else if (target === 'world') {
      injectChaos(text)
    } else {
      const agentId = target.replace('whisper_', '')
      whisperDirective(agentId, text)
    }
    setDirectiveText('')
  }

  return (
    <div className="panel">
      <div className="ph">
        <div className="ph-icon" style={{ background: 'rgba(167,139,250,.18)' }}>🎬</div>
        <span className="ph-title">Director</span>
      </div>

      <div className="pb">
        {/* Narrative Flow Mode: Dramatic Phases vs Direct Conversation */}
        <div style={{
          padding: '10px 12px',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          marginBottom: '14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em', color: phasesEnabled ? 'var(--amber)' : '#38bdf8' }}>
              {phasesEnabled ? '🎭 Dramatic Arc (20 Phases)' : '💬 Direct Conversation'}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--t4)' }}>
              {phasesEnabled ? 'Scripted Escalation' : 'Unscripted & Casual'}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              onClick={() => togglePhases(true)}
              style={{
                flex: 1,
                padding: '5px 8px',
                fontSize: '11px',
                fontWeight: 700,
                borderRadius: '5px',
                border: `1px solid ${phasesEnabled ? 'rgba(245,166,35,0.5)' : 'rgba(255,255,255,0.08)'}`,
                background: phasesEnabled ? 'rgba(245,166,35,0.18)' : 'rgba(0,0,0,0.25)',
                color: phasesEnabled ? 'var(--amber)' : 'var(--t3)',
                cursor: 'pointer',
              }}
            >
              🎭 20-Beat Arc
            </button>
            <button
              type="button"
              onClick={() => togglePhases(false)}
              style={{
                flex: 1,
                padding: '5px 8px',
                fontSize: '11px',
                fontWeight: 700,
                borderRadius: '5px',
                border: `1px solid ${!phasesEnabled ? 'rgba(56,189,248,0.5)' : 'rgba(255,255,255,0.08)'}`,
                background: !phasesEnabled ? 'rgba(56,189,248,0.18)' : 'rgba(0,0,0,0.25)',
                color: !phasesEnabled ? '#38bdf8' : 'var(--t3)',
                cursor: 'pointer',
              }}
            >
              💬 Direct Convo
            </button>
          </div>
        </div>

        {/* Pacing Speed (when Auto Mode is active) */}
        {auto && (
          <div style={{
            padding: '10px 12px',
            background: 'rgba(74, 222, 128, 0.08)',
            border: '1px solid rgba(74, 222, 128, 0.22)',
            borderRadius: '8px',
            marginBottom: '14px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
              <span style={{ color: '#4ade80', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '5px' }}>
                🟢 Auto-Play Active
              </span>
              <span style={{ color: 'var(--muted)', fontSize: '11px' }}>
                {isProcessing ? '⏳ In flight…' : `Next in ${autoCountdown ?? 0}s`}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '4px' }}>
              {[
                { label: '⚡ Fast (2s)', val: 2000 },
                { label: '🎬 Normal (3.5s)', val: 3500 },
                { label: '☕ Relaxed (5s)', val: 5000 },
              ].map(p => (
                <button
                  key={p.val}
                  type="button"
                  onClick={() => setAutoPacing(p.val)}
                  style={{
                    flex: 1,
                    padding: '4px 6px',
                    fontSize: '10px',
                    fontWeight: 600,
                    borderRadius: '4px',
                    background: autoDelay === p.val ? 'rgba(74, 222, 128, 0.3)' : 'rgba(0,0,0,0.35)',
                    border: autoDelay === p.val ? '1px solid #4ade80' : '1px solid rgba(255,255,255,0.1)',
                    color: autoDelay === p.val ? '#fff' : '#94a3b8',
                    cursor: 'pointer',
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* World State Overview */}
        <div className="sec">🌍 Atmosphere &amp; Stage</div>
        <div className="wcard" style={{ marginBottom: '14px' }}>
          <div className="wrow">
            <span className="wl">📍 Location</span>
            <span className="wv" style={{ fontWeight: 600 }}>{world.location}</span>
          </div>
          <div className="wrow">
            <span className="wl">💡 Lighting</span>
            <span className="wv" style={{ fontStyle: 'italic', opacity: 0.85 }}>{world.lighting}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span className="wl">🔥 Dramatic Tension</span>
              <span style={{ fontWeight: 800, color: 'var(--amber)' }}>{Math.round((vitals.tension || 0.5) * 100)}%</span>
            </div>
            <div className="tension-track">
              <div className="tension-fill" style={{ width: `${(vitals.tension || 0.5) * 100}%` }}/>
            </div>
          </div>
        </div>

        {/* Props Pills */}
        {world.props?.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <div className="sec">📦 Props in Play</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {world.props.map(p => (
                <span
                  key={p.id}
                  title={p.description}
                  style={{
                    fontSize: '11px',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: p.owner === 'world' ? 'var(--muted)' : 'var(--cyan)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span>{p.owner === 'world' ? '🌐' : '👤'}</span>
                  <span>{p.id.replace(/_/g, ' ')}</span>
                  {p.owner !== 'world' && (
                    <span style={{ opacity: 0.6, fontSize: '9px' }}>({p.owner})</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Unified Direct Scene Form */}
        <div className="sec">✨ Direct the Scene</div>
        <form onSubmit={handleDirect} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--t3)', whiteSpace: 'nowrap' }}>Direct to:</span>
            <select
              className="psel"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="world">🌍 Entire Stage (Event / Twist)</option>
              {agents.length > 0 && (
                <optgroup label="🗣️ Manual Dialogue (In-Character)">
                  {agents.map(a => (
                    <option key={`speak_${a.id}`} value={`speak_${a.id}`}>🗣️ Speak as {a.id}</option>
                  ))}
                </optgroup>
              )}
              {agents.length > 0 && (
                <optgroup label="🤫 Secret Director Whisper">
                  {agents.map(a => (
                    <option key={`whisper_${a.id}`} value={`whisper_${a.id}`}>🤫 Whisper to {a.id}</option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>

          <input 
            type="text" 
            placeholder={
              target === 'world' 
                ? "E.g., 'The delivery driver rings the doorbell'…" 
                : target.startsWith('speak_')
                ? `Say dialogue aloud as ${target.replace('speak_', '')}…`
                : `Secret in-ear prompt for ${target.replace('whisper_', '')}…`
            }
            value={directiveText} 
            onChange={(e) => setDirectiveText(e.target.value)}
          />

          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {[
              "Doorbell rings",
              "Phone notification chimes",
              "Playfully tease them",
              "Bring up the secret",
            ].map(preset => (
              <button
                key={preset}
                type="button"
                onClick={() => setDirectiveText(preset)}
                style={{
                  fontSize: 10,
                  padding: '3px 7px',
                  borderRadius: 4,
                  border: '1px solid var(--border)',
                  background: 'var(--s2)',
                  color: 'var(--t3)',
                  cursor: 'pointer',
                }}
              >
                {preset}
              </button>
            ))}
          </div>

          <button 
            type="submit" 
            style={{
              marginTop: 4,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '8px 12px', borderRadius: 8, border: 'none',
              background: target === 'world'
                ? 'linear-gradient(135deg, var(--amber), #d97706)'
                : target.startsWith('speak_')
                ? 'linear-gradient(135deg, #38bdf8, #6366f1)'
                : 'linear-gradient(135deg, var(--purple), #7c3aed)',
              color: '#000',
              fontWeight: 800,
              fontSize: 12,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            }}
          >
            {target === 'world' 
              ? '⚡ Inject Plot Event' 
              : target.startsWith('speak_')
              ? `🗣️ Speak Line as ${target.replace('speak_', '')}`
              : `🤫 Whisper to ${target.replace('whisper_', '')}`}
          </button>
        </form>
      </div>
    </div>
  )
}

