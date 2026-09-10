import { useEffect, useRef, useState } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'

export function BackstagePanel() {
  const { agents, messages, monologues, insights = [], forceEmotion, forceRelationship } = useSimulationContext()
  const [tab, setTab] = useState('vitals')
  const monoRef = useRef(null)
  const insightsRef = useRef(null)

  const lastSpk = [...messages].reverse().find(m => m.agent_id)?.agent_id

  useEffect(() => {
    if (tab === 'thoughts' && monoRef.current) {
      monoRef.current.scrollTop = monoRef.current.scrollHeight
    } else if (tab === 'insights' && insightsRef.current) {
      insightsRef.current.scrollTop = insightsRef.current.scrollHeight
    }
  }, [tab, monologues, insights])

  // Automatically switch to thoughts when a new one arrives
  useEffect(() => {
    if (monologues.length > 0 && tab !== 'insights' && tab !== 'relations') {
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
        <button 
          className={`tab ${tab === 'insights' ? 'active' : ''}`} 
          onClick={() => setTab('insights')}
        >
          💡 Insights {insights.length > 0 && (
            <span style={{ marginLeft: 4, fontSize: 10, background: 'rgba(252,211,77,.2)', color: 'var(--amber)', borderRadius: 4, padding: '1px 5px' }}>
              {insights.length}
            </span>
          )}
        </button>
        <button 
          className={`tab ${tab === 'relations' ? 'active' : ''}`} 
          onClick={() => setTab('relations')}
        >
          💞 Relations
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

      {tab === 'insights' && (
        <div className="pb">
          <div className="mono-stream" ref={insightsRef}>
            {insights.length === 0 && (
              <div className="mempty">Synthesized reflections appear here<br/>as characters analyze events…</div>
            )}
            {insights.map((ins, i) => {
              const idx = agents.findIndex(a => a.id === ins.agent_id)
              const col = agentColor(idx >= 0 ? idx : 0)
              return (
                <div key={i} className="mcard" style={{ borderLeftColor: col, background: 'rgba(252, 211, 77, 0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div className="mwho" style={{ color: col }}>{ins.agent_id}</div>
                    <span style={{ fontSize: 10, color: 'var(--amber)', fontFamily: 'JetBrains Mono, monospace' }}>
                      Turn {ins.turn ?? '?'}
                    </span>
                  </div>
                  <div className="mtext" style={{ color: '#e2e8f0' }}>💡 {ins.insight}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {tab === 'relations' && (
        <div className="pb">
          {agents.length < 2 && (
            <div className="mempty">At least two characters are required<br/>to model interpersonal relationships.</div>
          )}
          {agents.map((ag, i) => {
            const srcCol = agentColor(i)
            const otherAgents = agents.filter(other => other.id !== ag.id)
            if (otherAgents.length === 0) return null

            return (
              <div key={ag.id} style={{ marginBottom: 14 }}>
                {otherAgents.map((target, j) => {
                  const tgtIdx = agents.findIndex(a => a.id === target.id)
                  const tgtCol = agentColor(tgtIdx >= 0 ? tgtIdx : j)
                  const rel = ag.relationships?.[target.id] ?? { trust: 0.5, affinity: 0.5, fear: 0.0, dominance: 0.5 }

                  return (
                    <div key={target.id} className="vcard" style={{ borderLeft: `3px solid ${srcCol}`, marginBottom: 8 }}>
                      <div className="vname" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, marginBottom: 8 }}>
                        <div className="vdot" style={{ background: srcCol }}>{ag.id.substring(0, 2).toUpperCase()}</div>
                        <span style={{ fontWeight: 700, color: srcCol }}>{ag.id}</span>
                        <span style={{ color: 'var(--t4)', fontSize: 11 }}>➔</span>
                        <div className="vdot" style={{ background: tgtCol }}>{target.id.substring(0, 2).toUpperCase()}</div>
                        <span style={{ fontWeight: 600, color: tgtCol }}>{target.id}</span>
                      </div>

                      {[
                        ['trust', '🤝', 'Trust', 'var(--cyan)'],
                        ['affinity', '💖', 'Affinity', 'var(--pink)'],
                        ['fear', '😨', 'Fear', 'var(--orange)'],
                        ['dominance', '👑', 'Dominance', 'var(--purple)'],
                      ].map(([metric, icon, label, color]) => {
                        const val = rel[metric] ?? 0.5
                        return (
                          <div key={metric} className="vrow" style={{ marginTop: 4 }}>
                            <span className="vlbl" style={{ color, minWidth: 84, fontSize: 11 }}>{icon} {label}</span>
                            <input
                              type="range" min="0" max="1" step="0.05"
                              value={val}
                              onChange={(e) => forceRelationship(ag.id, target.id, metric, parseFloat(e.target.value))}
                              style={{ flex: 1, accentColor: color, '--c': color }}
                            />
                            <span className="vpct" style={{ color, minWidth: 32, textAlign: 'right', fontSize: 11 }}>
                              {Math.round(val * 100)}%
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
