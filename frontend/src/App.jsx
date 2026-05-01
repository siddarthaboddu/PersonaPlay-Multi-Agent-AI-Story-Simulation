import { useState, useEffect, useRef } from 'react'

// ── Colour palette per character index ──────────────────────────────
const CHAR_COLORS = ['#8b5cf6','#06b6d4','#ec4899','#f59e0b','#22c55e','#ef4444']
const charColor = (i) => CHAR_COLORS[i % CHAR_COLORS.length]

// ── Config Modal ─────────────────────────────────────────────────────
function ConfigModal({ isOpen, onClose, onSave, onTest, testResults }) {
  const [agents, setAgents] = useState([
    { id: "Alex", hidden_agenda: "Wants to convince Jamie to skip college and drive to Mexico. Secretly terrified of growing up.", model_config: { provider: "lm_studio", base_url: "http://localhost:1234/v1", model_name: "local-model", api_key: "" } },
    { id: "Jamie", hidden_agenda: "Just realized the mysterious duffel bag in the back belongs to a dangerous cartel. Wants to get home immediately without panicking Alex.", model_config: { provider: "lm_studio", base_url: "http://localhost:1234/v1", model_name: "local-model", api_key: "" } }
  ])

  if (!isOpen) return null

  const handleChange = (i, field, value) => {
    const a = [...agents]
    if (field === 'model_config.provider') {
      a[i].model_config.provider = value
      if (value === 'lm_studio') { a[i].model_config.base_url = "http://localhost:1234/v1"; a[i].model_config.model_name = "local-model" }
      else if (value === 'openrouter') { a[i].model_config.base_url = "https://openrouter.ai/api/v1"; a[i].model_config.model_name = "google/gemini-1.5-pro" }
      else if (value === 'google') { a[i].model_config.base_url = ""; a[i].model_config.model_name = "gemini-1.5-pro-latest" }
    } else if (field.startsWith('model_config.')) {
      a[i].model_config[field.split('.')[1]] = value
    } else { a[i][field] = value }
    setAgents(a)
  }

  const statusBadge = (id) => {
    const s = testResults[id]
    if (!s) return <span className="char-status-badge badge-idle">Idle</span>
    if (s.status === 'loading') return <span className="char-status-badge badge-loading">Testing…</span>
    if (s.status === 'ok') return <span className="char-status-badge badge-ok">✓ Connected</span>
    return <span className="char-status-badge badge-err">✗ Error</span>
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-title">🎭 Actor Roster</div>
        {agents.map((ag, i) => (
          <div key={i} className="char-card">
            <div className="char-card-header">
              <div style={{ width:24, height:24, borderRadius:'50%', background: charColor(i), display:'flex', alignItems:'center', justifyContent:'center', fontSize:10, fontWeight:700, color:'white', flexShrink:0 }}>
                {ag.id.substring(0,2).toUpperCase()}
              </div>
              <input type="text" placeholder="Character name" value={ag.id} onChange={e => handleChange(i,'id',e.target.value)} style={{flex:1, marginBottom:0}} />
              <button onClick={() => onTest(ag.id, ag.model_config)} className="btn-ghost" style={{width:'auto', padding:'5px 12px', flexShrink:0}}>Test</button>
              {statusBadge(ag.id)}
            </div>
            {testResults[ag.id]?.status === 'error' && <div style={{color:'#ef4444', fontSize:11, marginBottom:8, padding:'4px 8px', background:'rgba(239,68,68,0.08)', borderRadius:6}}>{testResults[ag.id].message}</div>}
            <input type="text" placeholder="🕵️ Hidden Agenda (the AI uses this privately)" value={ag.hidden_agenda} onChange={e => handleChange(i,'hidden_agenda',e.target.value)} />
            <div style={{display:'flex', gap:8}}>
              <select value={ag.model_config.provider} onChange={e => handleChange(i,'model_config.provider',e.target.value)} style={{flex:1}}>
                <option value="lm_studio">LM Studio (Local)</option>
                <option value="openrouter">OpenRouter (Cloud)</option>
                <option value="google">Google GenAI</option>
              </select>
              <input type="text" placeholder="Model" value={ag.model_config.model_name} onChange={e => handleChange(i,'model_config.model_name',e.target.value)} style={{flex:1}} />
            </div>
            <input type="password" placeholder="API Key (optional)" value={ag.model_config.api_key} onChange={e => handleChange(i,'model_config.api_key',e.target.value)} />
          </div>
        ))}
        <button className="btn-ghost" style={{width:'100%'}} onClick={() => setAgents([...agents,{ id:`Character_${agents.length+1}`, hidden_agenda:'', model_config:{ provider:'lm_studio', base_url:'http://localhost:1234/v1', model_name:'local-model', api_key:'' }}])}>
          + Add Character
        </button>
        <div className="modal-footer">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={() => onSave(agents)}>Save & Apply</button>
        </div>
      </div>
    </div>
  )
}

// ── Main App ─────────────────────────────────────────────────────────
export default function App() {
  const [messages, setMessages]     = useState([{ content: "[SYSTEM]: Ready to begin simulation…", type: "action" }])
  const [monologues, setMonologues] = useState([])
  const [vitals, setVitals]         = useState({ tension: 0.5, energy: 0.8 })
  const [command, setCommand]       = useState("")
  const [sceneInput, setSceneInput] = useState("")
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [testResults, setTestResults]   = useState({})
  const [isAutoPlay, setIsAutoPlay]     = useState(false)
  const [isTTSEnabled, setIsTTSEnabled] = useState(false)
  const [worldState, setWorldState]     = useState({ location:"Unknown", lighting:"Unknown", props:[] })
  const [agentsStatus, setAgentsStatus] = useState([])
  const [wsConnected, setWsConnected]   = useState(false)

  const wsRef             = useRef(null)
  const scriptRef         = useRef(null)
  const monoRef           = useRef(null)
  const autoPlayRef       = useRef(false)
  const ttsRef            = useRef(false)
  const autoPlayTimerRef  = useRef(null)

  useEffect(() => { autoPlayRef.current = isAutoPlay }, [isAutoPlay])
  useEffect(() => { ttsRef.current = isTTSEnabled }, [isTTSEnabled])

  const speakText = (text, name) => {
    if (!('speechSynthesis' in window) || !ttsRef.current) return
    const clean = text.replace(/\[.*?\]/g,'').trim()
    if (!clean) return
    const u = new SpeechSynthesisUtterance(clean)
    u.pitch = 0.8 + ((name.split('').reduce((a,c) => a+c.charCodeAt(0),0) % 10) / 20)
    window.speechSynthesis.speak(u)
  }

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws")
    wsRef.current = ws

    ws.onopen = () => {
      setWsConnected(true)
      ws.send(JSON.stringify({ type:"get_state" }))
    }
    ws.onclose = () => setWsConnected(false)
    ws.onerror = () => setWsConnected(false)

    ws.onmessage = (ev) => {
      const d = JSON.parse(ev.data)
      if (d.type === "dialogue" || d.type === "action") {
        setMessages(p => [...p, d])
        if (d.type === "dialogue") speakText(d.content, d.agent_id || "")
      } else if (d.type === "monologue") {
        setMonologues(p => [...p, d])
      } else if (d.type === "world_update") {
        setWorldState(d.world)
      } else if (d.type === "agents_update") {
        setAgentsStatus(d.agents)
      } else if (d.type === "image_update") {
        setMessages(p => [...p, { type:"image", url:d.url, prompt:d.prompt }])
      } else if (d.type === "history_reset") {
        setMessages(d.messages); setMonologues(d.monologues)
      } else if (d.type === "vitals_update") {
        setVitals(d.vitals)
        if (autoPlayRef.current) {
          if (autoPlayTimerRef.current) clearTimeout(autoPlayTimerRef.current)
          autoPlayTimerRef.current = setTimeout(() => {
            if (autoPlayRef.current && wsRef.current?.readyState === WebSocket.OPEN)
              wsRef.current.send(JSON.stringify({ type:"next_turn" }))
            autoPlayTimerRef.current = null
          }, 3000)
        }
      } else if (d.type === "check_result") {
        setTestResults(p => ({...p, [d.agent_id]: d}))
      }
    }
    return () => ws.close()
  }, [])

  useEffect(() => { if (scriptRef.current) scriptRef.current.scrollTop = scriptRef.current.scrollHeight }, [messages])
  useEffect(() => { if (monoRef.current) monoRef.current.scrollTop = monoRef.current.scrollHeight }, [monologues])

  const send = (msg) => wsRef.current?.readyState === WebSocket.OPEN && wsRef.current.send(JSON.stringify(msg))

  const lastSpeaker = messages.filter(m => m.agent_id).slice(-1)[0]?.agent_id

  // ── Render message line ──────────────────────────────────────────
  const renderLine = (msg, i) => {
    if (msg.type === "image") return (
      <div key={i} className="script-line" style={{margin:'8px 0'}}>
        <div style={{fontSize:11, color:'var(--text-muted)', marginBottom:6, fontStyle:'italic'}}>🎬 {msg.prompt?.substring(0,80)}…</div>
        <img src={msg.url} alt="Scene" style={{width:'100%', borderRadius:10, border:'1px solid var(--border)'}} />
      </div>
    )
    if (msg.type === "dialogue" && msg.agent_id) {
      const idx = agentsStatus.findIndex(a => a.id === msg.agent_id)
      const col = charColor(idx >= 0 ? idx : 0)
      const text = msg.content.replace(/^[^:]+:\s*/,'')
      return (
        <div key={i} className="script-line type-dialogue">
          <div className="avatar-sm" style={{background: col}}>{msg.agent_id.substring(0,2).toUpperCase()}</div>
          <div className="dialogue-wrap">
            <div className="speaker-name" style={{color: col}}>{msg.agent_id}</div>
            <div className="dialogue-text">{text}</div>
          </div>
        </div>
      )
    }
    // action / system
    const isDirector = msg.content?.includes('[DIRECTOR')
    const isSystem   = msg.content?.includes('[SYSTEM') || msg.content?.includes('[SCENE') || msg.content?.includes('[ERROR')
    return (
      <div key={i} className={`script-line type-action ${isDirector ? 'director' : isSystem ? 'system' : ''}`}>
        {msg.content}
      </div>
    )
  }

  return (
    <div className="app-shell">
      {/* ── Topbar ── */}
      <div className="topbar">
        <div className="topbar-logo">
          <div className="logo-icon">🎭</div>
          <div>
            <div>PersonaPlay <span style={{color:'var(--purple)'}}>Pro</span></div>
            <div className="logo-sub">Multi-Agent Theater Engine</div>
          </div>
        </div>

        <div className="topbar-center">
          <button className="pill-btn btn-start" style={{borderRadius:20}} onClick={() => send({type:"start_scene"})}>▶ Start</button>
          <button className="pill-btn btn-pause" style={{borderRadius:20}} onClick={() => { setIsAutoPlay(false); setMessages(p=>[...p,{type:'action',content:'[SYSTEM]: ⏸ Paused.'}]) }}>⏸ Pause</button>
          <button className="pill-btn btn-stop" style={{borderRadius:20}} onClick={() => { setIsAutoPlay(false); send({type:"stop_scene"}) }}>⏹ Stop</button>
          <div style={{width:1, height:18, background:'var(--border)', margin:'0 4px'}} />
          <button className="pill-btn" style={{borderRadius:20}} onClick={() => send({type:"next_turn"})}>⚡ Next Turn</button>
          <button className="pill-btn btn-rewind" style={{borderRadius:20}} onClick={() => send({type:"rewind_turns", turns:3})}>⏪ Rewind</button>
        </div>

        <div className="topbar-right">
          <div className="ws-indicator">
            <div className={`ws-dot ${wsConnected ? '' : 'offline'}`} />
            {wsConnected ? 'Live' : 'Offline'}
          </div>
          <button className="pill-btn" onClick={() => send({type:"export_script"})}>⬇ Export</button>
          <button className="pill-btn btn-primary" style={{borderRadius:20, fontSize:11}} onClick={() => setIsConfigOpen(true)}>⚙ Configure</button>
        </div>
      </div>

      {/* ── Dashboard ── */}
      <div className="dashboard">
        <ConfigModal isOpen={isConfigOpen} onClose={() => setIsConfigOpen(false)}
          onSave={agents => { send({type:"configure_scene", agents}); setIsConfigOpen(false) }}
          onTest={(id, cfg) => { setTestResults(p=>({...p,[id]:{status:'loading'}})); send({type:"check_model", agent_id:id, model_config:cfg}) }}
          testResults={testResults} />

        {/* ── LEFT: Director Panel ── */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-head-icon" style={{background:'rgba(139,92,246,0.2)'}}>🎬</div>
            <h2>Director</h2>
          </div>
          <div className="panel-body">

            {/* Auto-play & TTS toggles */}
            <div className="toggle-row">
              <span className="toggle-label">🎞 Auto-Play</span>
              <label className="toggle-switch">
                <input type="checkbox" checked={isAutoPlay} onChange={e => setIsAutoPlay(e.target.checked)} />
                <span className="toggle-track" />
              </label>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">🔊 Voice (TTS)</span>
              <label className="toggle-switch">
                <input type="checkbox" checked={isTTSEnabled} onChange={e => setIsTTSEnabled(e.target.checked)} />
                <span className="toggle-track" />
              </label>
            </div>

            <div className="divider" />

            {/* Scene World */}
            <div className="section-label">🌍 World State</div>
            <div className="world-card">
              <div className="world-card-row"><span className="wlabel">📍 Location</span><span className="wvalue">{worldState.location}</span></div>
              <div className="world-card-row"><span className="wlabel">💡 Lighting</span><span className="wvalue">{worldState.lighting}</span></div>
              <div className="world-card-row" style={{marginTop:8, flexDirection:'column', alignItems:'flex-start', gap:4}}>
                <span className="wlabel" style={{fontSize:10}}>🔥 Scene Tension — {Math.round((vitals.tension||0.5)*100)}%</span>
                <div className="tension-bar" style={{width:'100%'}}>
                  <div className="tension-fill" style={{width:`${(vitals.tension||0.5)*100}%`}} />
                </div>
                <input type="range" min="0" max="1" step="0.05" value={vitals.tension||0.5}
                  onChange={e => send({type:"force_scene_tension", value:parseFloat(e.target.value)})}
                  style={{width:'100%', marginTop:2, accentColor:'var(--amber)'}} />
              </div>
            </div>

            {/* Props */}
            {worldState.props.length > 0 && <>
              <div className="section-label">🧳 Props</div>
              {worldState.props.map(p => (
                <div key={p.id} className="prop-row">
                  <span className="prop-name">🎁 {p.id.replace(/_/g,' ')}</span>
                  <select className="prop-select" value={p.owner}
                    onChange={e => send({type:"force_give_prop", prop_id:p.id, owner:e.target.value})}>
                    <option value="Nobody">Nobody</option>
                    {agentsStatus.map(a => <option key={a.id} value={a.id}>{a.id}</option>)}
                  </select>
                </div>
              ))}
            </>}

            <div className="divider" />

            {/* Move scene */}
            <div className="section-label">🚀 Teleport Scene</div>
            <form onSubmit={e => { e.preventDefault(); if(sceneInput.trim()){ send({type:"change_scene", location:sceneInput}); setSceneInput("") }}} style={{display:'flex', gap:6}}>
              <input type="text" placeholder="New location…" value={sceneInput} onChange={e => setSceneInput(e.target.value)} style={{flex:1}} />
              <button type="submit" className="btn-ghost" style={{width:'auto', padding:'8px 12px', flexShrink:0}}>Go</button>
            </form>

            {/* Director command */}
            <div className="section-label">⚡ Inject Chaos</div>
            <form onSubmit={e => { e.preventDefault(); if(command.trim()){ send({type:"director_command", command}); setMessages(p=>[...p,{type:'action',content:`[DIRECTOR INJECTS]: ${command}`}]); setCommand("") }}} style={{display:'flex', flexDirection:'column', gap:6}}>
              <input type="text" placeholder="Type a dramatic event…" value={command} onChange={e => setCommand(e.target.value)} />
              <button type="submit" className="btn-chaos">🔥 Inject</button>
            </form>

          </div>
        </div>

        {/* ── CENTER: Theater Panel ── */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-head-icon" style={{background:'rgba(6,182,212,0.2)'}}>🎭</div>
            <h2>Theater</h2>
            {agentsStatus.length > 0 && <span style={{marginLeft:'auto', fontSize:10, color:'var(--text-muted)'}}>{worldState.location}</span>}
          </div>

          {/* Stage */}
          <div className="stage-wrap">
            <div className="stage-label">Stage</div>
            {agentsStatus.map((agent, i) => {
              const col = charColor(i)
              const left = 15 + ((i * 40) % 65) + (agent.emotions?.energy ?? 0.5) * 15
              const top  = 20 + ((i * 18) % 35) + (agent.emotions?.tension ?? 0.5) * 18
              const speaking = lastSpeaker === agent.id
              return (
                <div key={agent.id} className={`actor-avatar ${speaking ? 'speaking' : ''}`}
                  style={{ left:`${left}%`, top:`${top}%`, background: col, transform: `translate(-50%,-50%)` }}>
                  {agent.id.substring(0,2).toUpperCase()}
                  <div className="actor-name-tag">{agent.id}</div>
                </div>
              )
            })}
            <div className="stage-floor" />
          </div>

          {/* Script feed */}
          <div className="script-feed" ref={scriptRef}>
            {messages.map((msg, i) => renderLine(msg, i))}
          </div>
        </div>

        {/* ── RIGHT: Backstage Panel ── */}
        <div className="panel">
          <div className="panel-head">
            <div className="panel-head-icon" style={{background:'rgba(236,72,153,0.2)'}}>🧠</div>
            <h2>Backstage</h2>
          </div>
          <div className="panel-body">

            {/* Agent emotion sliders */}
            {agentsStatus.map((agent, i) => {
              const col = charColor(i)
              return (
                <div key={agent.id} className="agent-vitals-card">
                  <div className="agent-vitals-name">
                    <div className="avatar-dot" style={{background: col}}>{agent.id.substring(0,2).toUpperCase()}</div>
                    {agent.id}
                    {lastSpeaker === agent.id && <span style={{marginLeft:'auto', fontSize:9, color: col, fontWeight:700, letterSpacing:1}}>SPEAKING</span>}
                  </div>
                  {[['tension','🔥','#ef4444'],['energy','⚡','#22c55e'],['affection','💜','#ec4899'],['suspicion','👁','#f59e0b']].map(([stat,icon,color]) => (
                    <div key={stat} className="vital-row">
                      <span className="vital-label" style={{color}}>{icon} {stat.charAt(0).toUpperCase()+stat.slice(1)}</span>
                      <input type="range" min="0" max="1" step="0.05" className="vital-range"
                        value={agent.emotions?.[stat] ?? 0.5}
                        onChange={e => send({type:"force_emotion", agent_id:agent.id, emotion:stat, value:parseFloat(e.target.value)})}
                        style={{accentColor: color}} />
                      <span className="vital-pct">{Math.round((agent.emotions?.[stat]??0.5)*100)}%</span>
                    </div>
                  ))}
                </div>
              )
            })}

            {agentsStatus.length > 0 && <div className="divider" />}

            {/* Internal monologue stream */}
            <div className="section-label">💭 Inner Thoughts</div>
            <div className="mono-stream" ref={monoRef}>
              {monologues.length === 0 && <div style={{fontSize:12, color:'var(--text-muted)', fontStyle:'italic', textAlign:'center', marginTop:8}}>Thoughts appear here during simulation…</div>}
              {monologues.map((msg, i) => {
                const idx = agentsStatus.findIndex(a => a.id === msg.agent_id)
                const col = charColor(idx >= 0 ? idx : 0)
                return (
                  <div key={i} className="mono-entry" style={{borderLeftColor: col+'66'}}>
                    <div className="mono-who" style={{color: col}}>{msg.agent_id}</div>
                    <div className="mono-text">{msg.content}</div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
