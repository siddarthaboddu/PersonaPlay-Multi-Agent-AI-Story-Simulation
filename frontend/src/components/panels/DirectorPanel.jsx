import { useState } from 'react'
import { useSimulationContext } from '../../context/useSimulationContext'

export function DirectorPanel() {
  const { 
    world, vitals, agents, injectChaos, whisperDirective, sendManualDialogue, pause,
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
        <div className="ph-icon" style={{ background: 'linear-gradient(135deg, rgba(245, 208, 97, 0.2), rgba(167, 139, 250, 0.2))' }}>🎬</div>
        <span className="ph-title">Director Studio</span>
      </div>

      <div className="pb">
        {/* Narrative Flow Mode: Human Realism vs Dramatic Scripted Phases */}
        <div style={{
          padding: '12px 14px',
          background: 'var(--s2)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-sm)',
          marginBottom: '4px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{
              fontSize: '11px',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: !phasesEnabled ? '#38bdf8' : 'var(--gold)'
            }}>
              {!phasesEnabled ? '👤 Human Realism' : '🎭 Dramatic 20-Beat Arc'}
            </span>
            <span style={{ fontSize: '10.5px', color: 'var(--t4)', fontStyle: 'italic' }}>
              {!phasesEnabled ? 'Unscripted Flow' : 'Escalation Curve'}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              onClick={() => togglePhases(false)}
              style={{
                flex: 1,
                padding: '6px 10px',
                fontSize: '11.5px',
                fontFamily: 'var(--font-sans)',
                fontWeight: !phasesEnabled ? 800 : 600,
                borderRadius: '8px',
                border: `1px solid ${!phasesEnabled ? 'rgba(56, 189, 248, 0.5)' : 'var(--border)'}`,
                background: !phasesEnabled ? 'rgba(56, 189, 248, 0.18)' : 'rgba(0, 0, 0, 0.25)',
                color: !phasesEnabled ? '#38bdf8' : 'var(--t3)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: !phasesEnabled ? '0 0 12px rgba(56, 189, 248, 0.2)' : 'none',
              }}
            >
              👤 Human Mode
            </button>
            <button
              type="button"
              onClick={() => togglePhases(true)}
              style={{
                flex: 1,
                padding: '6px 10px',
                fontSize: '11.5px',
                fontFamily: 'var(--font-sans)',
                fontWeight: phasesEnabled ? 800 : 600,
                borderRadius: '8px',
                border: `1px solid ${phasesEnabled ? 'rgba(245, 208, 97, 0.5)' : 'var(--border)'}`,
                background: phasesEnabled ? 'rgba(245, 208, 97, 0.18)' : 'rgba(0, 0, 0, 0.25)',
                color: phasesEnabled ? 'var(--gold)' : 'var(--t3)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: phasesEnabled ? '0 0 12px rgba(245, 208, 97, 0.2)' : 'none',
              }}
            >
              🎭 20-Beat Arc
            </button>
          </div>
        </div>

        {/* Pacing Speed (when Auto Mode is active) */}
        {auto && (
          <div style={{
            padding: '12px 14px',
            background: 'linear-gradient(135deg, rgba(52, 211, 153, 0.1), rgba(16, 185, 129, 0.05))',
            border: '1px solid rgba(52, 211, 153, 0.3)',
            borderRadius: 'var(--r-sm)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            boxShadow: '0 0 16px rgba(52, 211, 153, 0.1)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
              <span style={{ color: '#34d399', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34d399', boxShadow: '0 0 6px #34d399' }} />
                Auto-Play Active
              </span>
              <span style={{ color: 'var(--t3)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                {isProcessing ? '⏳ Thinking…' : `Next in ${autoCountdown ?? 0}s`}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '5px' }}>
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
                    padding: '5px 8px',
                    fontSize: '10.5px',
                    fontFamily: 'var(--font-sans)',
                    fontWeight: 700,
                    borderRadius: '6px',
                    background: autoDelay === p.val ? 'rgba(52, 211, 153, 0.3)' : 'rgba(0,0,0,0.3)',
                    border: autoDelay === p.val ? '1px solid #34d399' : '1px solid var(--border)',
                    color: autoDelay === p.val ? '#ffffff' : 'var(--t3)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* World State Overview */}
        <div className="sec">🌍 Atmosphere &amp; Setting</div>
        <div className="wcard">
          <div className="wrow">
            <span className="wl">📍 Location</span>
            <span className="wv" style={{ fontWeight: 600, color: 'var(--t1)' }}>{world.location}</span>
          </div>
          <div className="wrow" style={{ alignItems: 'flex-start' }}>
            <span className="wl" style={{ flexShrink: 0 }}>💡 Lighting</span>
            <span className="wv" style={{ fontStyle: 'italic', color: 'var(--t2)', fontSize: 12, lineHeight: 1.4, whiteSpace: 'normal', textAlign: 'right' }}>
              "{world.lighting}"
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span className="wl">🔥 Dramatic Tension</span>
              <span style={{ fontWeight: 800, color: 'var(--gold)', fontFamily: 'var(--font-mono)' }}>
                {Math.round((vitals.tension || 0.5) * 100)}%
              </span>
            </div>
            <div className="tension-track">
              <div className="tension-fill" style={{ width: `${(vitals.tension || 0.5) * 100}%` }}/>
            </div>
          </div>
        </div>

        {/* Props Pills */}
        {world.props?.length > 0 && (
          <div>
            <div className="sec">📦 Items on Stage</div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {world.props.map(p => (
                <span
                  key={p.id}
                  title={p.description}
                  style={{
                    fontSize: '11px',
                    padding: '4px 9px',
                    borderRadius: 'var(--r-pill)',
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border)',
                    color: p.owner === 'world' ? 'var(--t3)' : 'var(--cyan)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.3)'
                  }}
                >
                  <span style={{ fontSize: 10 }}>{p.owner === 'world' ? '🌐' : '👤'}</span>
                  <span style={{ fontWeight: 600 }}>{p.id.replace(/_/g, ' ')}</span>
                  {p.owner !== 'world' && (
                    <span style={{ opacity: 0.6, fontSize: '9.5px', color: 'var(--t2)' }}>({p.owner})</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Unified Direct Scene Form */}
        <div className="sec">✨ Direct the Scene</div>
        <form onSubmit={handleDirect} style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--t3)', whiteSpace: 'nowrap' }}>Target:</span>
            <select
              className="psel"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="world">🌍 Entire Stage (Plot Twist / Chaos)</option>
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
                ? "E.g., 'A loud knock at the front door echoes'…" 
                : target.startsWith('speak_')
                ? `Say dialogue aloud as ${target.replace('speak_', '')}…`
                : `Secret directive for ${target.replace('whisper_', '')}…`
            }
            value={directiveText} 
            onChange={(e) => setDirectiveText(e.target.value)}
          />

          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
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
                  fontSize: 10.5,
                  padding: '3px 8px',
                  borderRadius: 6,
                  border: '1px solid var(--border)',
                  background: 'rgba(255, 255, 255, 0.03)',
                  color: 'var(--t3)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {preset}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            {auto && (
              <button
                type="button"
                onClick={pause}
                style={{
                  padding: '9px 14px',
                  borderRadius: 9,
                  border: '1px solid rgba(245, 208, 97, 0.45)',
                  background: 'rgba(245, 208, 97, 0.15)',
                  color: 'var(--gold)',
                  fontWeight: 800,
                  fontSize: 12,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
                title="Pause simulation"
              >
                ⏸ Pause
              </button>
            )}
            <button 
              type="submit" 
              style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '9px 16px', borderRadius: 9, border: 'none',
                background: target === 'world'
                  ? 'linear-gradient(135deg, var(--gold), #d97706)'
                  : target.startsWith('speak_')
                  ? 'linear-gradient(135deg, #38bdf8, #6366f1)'
                  : 'linear-gradient(135deg, var(--purple), #7c3aed)',
                color: '#050711',
                fontWeight: 800,
                fontSize: 12,
                cursor: 'pointer',
                boxShadow: '0 4px 14px rgba(0, 0, 0, 0.4)',
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
              }}
            >
              {target === 'world' 
                ? '⚡ Inject Plot Event' 
                : target.startsWith('speak_')
                ? `🗣️ Speak Line as ${target.replace('speak_', '')}`
                : `🤫 Whisper to ${target.replace('whisper_', '')}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

