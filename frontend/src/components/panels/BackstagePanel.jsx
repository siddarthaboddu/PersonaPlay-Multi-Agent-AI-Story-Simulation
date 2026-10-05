import { useEffect, useRef, useState } from 'react'
import { useSimulationContext } from '../../context/useSimulationContext'
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
        <div className="ph-icon" style={{ background: 'linear-gradient(135deg, rgba(167, 139, 250, 0.2), rgba(244, 114, 182, 0.2))' }}>🧠</div>
        <span className="ph-title">Backstage Cognition</span>
      </div>
      <div className="tabs">
        <button 
          className={`tab ${tab === 'psychology' ? 'active' : ''}`} 
          onClick={() => setTab('psychology')}
        >
          <span>💭 Psychology</span>
          {combinedPsychology.length > 0 && (
            <span style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              background: 'rgba(167, 139, 250, 0.2)',
              color: 'var(--purple)',
              borderRadius: 'var(--r-pill)',
              padding: '1px 6px',
              fontWeight: 800
            }}>
              {combinedPsychology.length}
            </span>
          )}
        </button>
        <button 
          className={`tab ${tab === 'dynamics' ? 'active' : ''}`} 
          onClick={() => setTab('dynamics')}
        >
          <span>⚡ Dynamics &amp; Stances</span>
        </button>
      </div>

      {tab === 'psychology' && (
        <div className="pb">
          <div className="mono-stream" ref={streamRef}>
            {combinedPsychology.length === 0 && (
              <div className="mempty">
                <div style={{ fontSize: 24, marginBottom: 8 }}>💭</div>
                <div style={{ color: 'var(--t2)', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>Subconscious Feed Empty</div>
                <div>Inner monologues and synthesized strategic deductions will stream here as characters converse…</div>
              </div>
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
                    borderLeftColor: isInsight ? 'var(--gold)' : col,
                    background: isInsight 
                      ? 'linear-gradient(135deg, rgba(245, 208, 97, 0.08), rgba(22, 28, 48, 0.7))' 
                      : 'var(--s2)',
                    boxShadow: isInsight ? '0 0 16px rgba(245, 208, 97, 0.08)' : 'none'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div className="mwho" style={{ color: col, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: col }} />
                      <span>{item.agent_id}</span>
                    </div>
                    <span style={{ 
                      fontSize: '10px', 
                      color: isInsight ? 'var(--gold)' : 'var(--t4)', 
                      fontFamily: 'var(--font-mono)',
                      background: isInsight ? 'rgba(245, 208, 97, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                      border: `1px solid ${isInsight ? 'rgba(245, 208, 97, 0.3)' : 'transparent'}`,
                      padding: '2px 7px',
                      borderRadius: 'var(--r-pill)',
                      fontWeight: 700
                    }}>
                      {isInsight ? `💡 Insight • Turn ${item.turn ?? '?'}` : '💭 Private Thought'}
                    </span>
                  </div>
                  <div className="mtext" style={{ color: isInsight ? '#f8fafc' : 'var(--t2)', fontSize: '13px', fontStyle: 'italic', lineHeight: 1.6 }}>
                    "{item.content}"
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
              <div key={ag.id} className="vcard" style={{ marginBottom: 12 }}>
                <div className="vname">
                  <div className="vdot" style={{ background: `linear-gradient(135deg, ${col}, ${col}cc)` }}>
                    {ag.id.substring(0, 2).toUpperCase()}
                  </div>
                  <span style={{ fontSize: 13.5, fontWeight: 700 }}>{ag.id}</span>
                  {lastSpk === ag.id && <span className="spk-badge">LIVE SPEAKER</span>}
                </div>

                {ag.pending_whisper && (
                  <div style={{
                    margin: '6px 0 12px',
                    padding: '6px 10px',
                    borderRadius: 8,
                    background: 'rgba(167, 139, 250, 0.14)',
                    border: '1px solid rgba(167, 139, 250, 0.35)',
                    color: 'var(--purple)',
                    fontSize: 11.5,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    boxShadow: '0 0 12px rgba(167, 139, 250, 0.15)'
                  }}>
                    <span style={{ fontSize: 14 }}>🤫</span>
                    <div>
                      <span style={{ fontSize: 9.5, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 800, display: 'block', opacity: 0.8 }}>
                        In-Ear Directive
                      </span>
                      <span style={{ fontStyle: 'italic', color: '#f0f2fc' }}>"{ag.pending_whisper}"</span>
                    </div>
                  </div>
                )}

                {(ag.current_goal || ag.current_attention || ag.beliefs?.length > 0) && (
                  <div style={{ margin: '8px 0 12px', padding: '8px 10px', borderRadius: 8, background: 'rgba(167, 139, 250, 0.08)', border: '1px solid rgba(167, 139, 250, 0.18)', fontSize: 11.5, lineHeight: 1.5 }}>
                    <div style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--purple)', marginBottom: 4 }}>Current Priorities &amp; Beliefs</div>
                    {ag.current_goal && <div><b>Wants:</b> {ag.current_goal}</div>}
                    {ag.current_attention && <div><b>Notices:</b> {ag.current_attention}</div>}
                    {ag.beliefs?.slice(-2).map((belief, beliefIndex) => (
                      <div key={beliefIndex}><b>Believes:</b> {belief}</div>
                    ))}
                  </div>
                )}

                {/* Emotional Vitals */}
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--t4)', marginBottom: 6 }}>
                    Emotional Vitals
                  </div>
                  {[
                    ['tension', '🔥', '#fb7185'], 
                    ['energy', '⚡', '#34d399'], 
                    ['affection', '💜', '#f472b6'], 
                    ['suspicion', '👁', '#fbbf24']
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

                {/* Interpersonal Stance toward others */}
                {otherAgents.length > 0 && (
                  <div style={{ paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--t4)', marginBottom: 6 }}>
                      Pairwise Relationships
                    </div>
                    {otherAgents.map((target, j) => {
                      const tgtIdx = agents.findIndex(a => a.id === target.id)
                      const tgtCol = agentColor(tgtIdx >= 0 ? tgtIdx : j)
                      const rel = ag.relationships?.[target.id] ?? { trust: 0.5, affinity: 0.5, fear: 0.0, dominance: 0.5 }

                      return (
                        <div key={target.id} style={{ marginBottom: 8, background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: 8 }}>
                          <div style={{ fontSize: 11, color: 'var(--t3)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 5 }}>
                            <span>Toward</span>
                            <span style={{ color: tgtCol, fontWeight: 700 }}>{target.id}:</span>
                          </div>
                          {[
                            ['trust', '🤝', 'Trust', 'var(--cyan)'],
                            ['affinity', '💖', 'Affinity', 'var(--pink)'],
                          ].map(([metric, icon, label, color]) => {
                            const val = rel[metric] ?? 0.5
                            return (
                              <div key={metric} className="vrow" style={{ marginBottom: 4 }}>
                                <span className="vlbl" style={{ color, minWidth: 65, fontSize: 11 }}>{icon} {label}</span>
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
                )}
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

