import { useEffect, useRef, useState } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'

export function BackstagePanel() {
  const { agents, messages, monologues, forceEmotion } = useSimulationContext()
  const [tab, setTab] = useState('vitals')
  const monoRef = useRef(null)

  const lastSpk = [...messages].reverse().find(m => m.agent_id)?.agent_id

  useEffect(() => {
    if (tab === 'thoughts' && monoRef.current) {
      monoRef.current.scrollTop = monoRef.current.scrollHeight
    }
  }, [tab, monologues])

  // Automatically switch to thoughts when a new one arrives
  useEffect(() => {
    if (monologues.length > 0) {
      setTab('thoughts')
    }
  }, [monologues.length])

  return (
    <div className="panel">
      <div className="ph">
        <div className="ph-icon" style={{ background: 'rgba(249,168,212,.12)' }}>🧠</div>
        <span className="ph-title">Backstage</span>
      </div>
      <div className="tabs">
        <button 
          className={`tab ${tab === 'vitals' ? 'active' : ''}`} 
          onClick={() => setTab('vitals')}
        >
          ⚡ Vitals
        </button>
        <button 
          className={`tab ${tab === 'thoughts' ? 'active' : ''}`} 
          onClick={() => setTab('thoughts')}
        >
          💭 Thoughts {monologues.length > 0 && (
            <span style={{ marginLeft: 4, fontSize: 10, background: 'rgba(167,139,250,.2)', color: 'var(--purple)', borderRadius: 4, padding: '1px 5px' }}>
              {monologues.length}
            </span>
          )}
        </button>
      </div>

      {tab === 'vitals' && (
        <div className="pb">
          {agents.map((ag, i) => {
            const col = agentColor(i)
            return (
              <div key={ag.id} className="vcard">
                <div className="vname">
                  <div className="vdot" style={{ background: col }}>{ag.id.substring(0, 2).toUpperCase()}</div>
                  {ag.id}
                  {lastSpk === ag.id && <span className="spk-badge">LIVE</span>}
                </div>
                {[
                  ['tension', '🔥', '#fc8181'], 
                  ['energy', '⚡', '#4ade80'], 
                  ['affection', '💜', '#f9a8d4'], 
                  ['suspicion', '👁', '#fcd34d']
                ].map(([s, ic, c]) => (
                  <div key={s} className="vrow">
                    <span className="vlbl" style={{ color: c }}>{ic} {s.charAt(0).toUpperCase() + s.slice(1)}</span>
                    <input 
                      type="range" min="0" max="1" step="0.05"
                      value={ag.emotions?.[s] ?? 0.5}
                      onChange={(e) => forceEmotion(ag.id, s, parseFloat(e.target.value))}
                      style={{ flex: 1, accentColor: c, '--c': c }}
                    />
                    <span className="vpct" style={{ color: c }}>{Math.round((ag.emotions?.[s] ?? 0.5) * 100)}%</span>
                  </div>
                ))}
              </div>
            )
          })}
          {agents.length === 0 && (
            <div className="mempty">No agents loaded yet.<br/>Press Configure to set up your cast.</div>
          )}
        </div>
      )}

      {tab === 'thoughts' && (
        <div className="pb">
          <div className="mono-stream" ref={monoRef}>
            {monologues.length === 0 && (
              <div className="mempty">Inner thoughts appear here<br/>as the scene unfolds…</div>
            )}
            {monologues.map((m, i) => {
              const idx = agents.findIndex(a => a.id === m.agent_id)
              const col = agentColor(idx >= 0 ? idx : 0)
              return (
                <div key={i} className="mcard" style={{ borderLeftColor: col }}>
                  <div className="mwho" style={{ color: col }}>{m.agent_id}</div>
                  <div className="mtext">{m.content}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
