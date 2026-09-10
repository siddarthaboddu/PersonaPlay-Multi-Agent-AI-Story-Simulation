import { useEffect, useRef, useState } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'
import { agentColor } from '../../utils/colors'

export function BackstagePanel() {
  const { agents, messages, monologues, insights = [], forceEmotion, forceRelationship } = useSimulationContext()
  const [tab, setTab] = useState('psychology') // 'psychology' or 'dynamics'
  const streamRef = useRef(null)

  const lastSpk = [...messages].reverse().find(m => m.agent_id)?.agent_id

  // Auto-scroll stream when new items arrive
  useEffect(() => {
    if (tab === 'psychology' && streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight
    }
  }, [tab, monologues, insights])

  // Combine monologues and insights chronologically for Psychology feed
  const combinedPsychology = [
    ...monologues.map(m => ({ ...m, itemType: 'thought' })),
    ...insights.map(ins => ({ 
      agent_id: ins.agent_id, 
      content: ins.insight, 
      turn: ins.turn, 
      itemType: 'insight' 
    }))
  ]

  return (
    <div className="panel">
      <div className="ph">
        <div className="ph-icon" style={{ background: 'rgba(249,168,212,.12)' }}>🧠</div>
        <span className="ph-title">Backstage</span>
      </div>
      <div className="tabs">
        <button 
          className={`tab ${tab === 'psychology' ? 'active' : ''}`} 
          onClick={() => setTab('psychology')}
        >
          💭 Psychology {combinedPsychology.length > 0 && (
            <span style={{ marginLeft: 4, fontSize: 10, background: 'rgba(167,139,250,.2)', color: 'var(--purple)', borderRadius: 4, padding: '1px 5px' }}>
              {combinedPsychology.length}
            </span>
          )}
        </button>
        <button 
          className={`tab ${tab === 'dynamics' ? 'active' : ''}`} 
          onClick={() => setTab('dynamics')}
        >
          ⚡ Dynamics &amp; Relations
        </button>
      </div>

      {tab === 'psychology' && (
        <div className="pb">
          <div className="mono-stream" ref={streamRef}>
            {combinedPsychology.length === 0 && (
              <div className="mempty">Inner thoughts and tactical reflections<br/>will appear here as the scene unfolds…</div>
            )}
            {combinedPsychology.map((item, i) => {
              const idx = agents.findIndex(a => a.id === item.agent_id)
              const col = agentColor(idx >= 0 ? idx : 0)
              const isInsight = item.itemType === 'insight'

              return (
                <div 
                  key={i} 
                  className="mcard" 
                  style={{ 
                    borderLeftColor: col,
                    background: isInsight ? 'rgba(252, 211, 77, 0.05)' : undefined
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div className="mwho" style={{ color: col }}>{item.agent_id}</div>
                    <span style={{ 
                      fontSize: 10, 
                      color: isInsight ? 'var(--amber)' : 'var(--muted)', 
                      fontFamily: 'JetBrains Mono, monospace',
                      background: isInsight ? 'rgba(252,211,77,0.1)' : 'rgba(255,255,255,0.05)',
                      padding: '1px 6px',
                      borderRadius: 4
                    }}>
                      {isInsight ? `💡 Insight • Turn ${item.turn ?? '?'}` : '💭 Thought'}
                    </span>
                  </div>
                  <div className="mtext" style={{ color: isInsight ? '#e2e8f0' : undefined }}>
                    {item.content}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {tab === 'dynamics' && (
        <div className="pb">
          {agents.map((ag, i) => {
            const col = agentColor(i)
            const otherAgents = agents.filter(other => other.id !== ag.id)

            return (
              <div key={ag.id} className="vcard" style={{ marginBottom: 14 }}>
                <div className="vname">
                  <div className="vdot" style={{ background: col }}>{ag.id.substring(0, 2).toUpperCase()}</div>
                  {ag.id}
                  {lastSpk === ag.id && <span className="spk-badge">LIVE</span>}
                </div>

                {ag.pending_whisper && (
                  <div style={{
                    margin: '6px 0 10px',
                    padding: '5px 9px',
                    borderRadius: 6,
                    background: 'rgba(167,139,250,0.12)',
                    border: '1px solid rgba(167,139,250,0.3)',
                    color: 'var(--purple)',
                    fontSize: 11,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}>
                    <span>🤫</span>
                    <span style={{ fontStyle: 'italic', color: '#f0f2fc' }}>"{ag.pending_whisper}"</span>
                  </div>
                )}

                {/* Emotional Vitals */}
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

                {/* Interpersonal Stance toward others */}
                {otherAgents.map((target, j) => {
                  const tgtIdx = agents.findIndex(a => a.id === target.id)
                  const tgtCol = agentColor(tgtIdx >= 0 ? tgtIdx : j)
                  const rel = ag.relationships?.[target.id] ?? { trust: 0.5, affinity: 0.5, fear: 0.0, dominance: 0.5 }

                  return (
                    <div key={target.id} style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span>Stance toward</span>
                        <span style={{ color: tgtCol, fontWeight: 700 }}>{target.id}:</span>
                      </div>
                      {[
                        ['trust', '🤝', 'Trust', 'var(--cyan)'],
                        ['affinity', '💖', 'Affinity', 'var(--pink)'],
                      ].map(([metric, icon, label, color]) => {
                        const val = rel[metric] ?? 0.5
                        return (
                          <div key={metric} className="vrow" style={{ marginTop: 3 }}>
                            <span className="vlbl" style={{ color, minWidth: 70, fontSize: 11 }}>{icon} {label}</span>
                            <input
                              type="range" min="0" max="1" step="0.05"
                              value={val}
                              onChange={(e) => forceRelationship(ag.id, target.id, metric, parseFloat(e.target.value))}
                              style={{ flex: 1, accentColor: color, '--c': color }}
                            />
                            <span className="vpct" style={{ color, minWidth: 28, textAlign: 'right', fontSize: 11 }}>
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
          {agents.length === 0 && (
            <div className="mempty">No characters loaded yet.<br/>Open Configure to add actors.</div>
          )}
        </div>
      )}
    </div>
  )
}

