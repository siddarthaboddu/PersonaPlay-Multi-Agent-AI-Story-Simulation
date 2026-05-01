import { useState, useEffect, useRef } from 'react'

const COLORS = ['#a78bfa','#67e8f9','#f9a8d4','#fcd34d','#4ade80','#fc8181','#fb923c']
const cc = i => COLORS[i % COLORS.length]

const BEATS = [
  [0,3,'COLD OPEN'],   [4,7,'STATUS QUO'],    [8,12,'FIRST FRICTION'],
  [13,18,'ESCALATION'],[19,25,'COMPLICATION'],[26,32,'CONFRONTATION'],
  [33,40,'REVELATION'],[41,48,'POWER SHIFT'], [49,58,'CRISIS POINT'],
  [59,68,'CLIMAX I'],  [69,80,'CLIMAX II'],   [81,92,'BREAKING POINT'],
  [93,105,'FALLING ACTION'],[106,120,'RECKONING'],[121,135,'UNEASY PEACE'],
  [136,155,'NEW COMPLICATION'],[156,175,'SECOND ARC'],[176,200,'SECOND CLIMAX'],
  [201,999,'EPILOGUE'],
]
const getBeat = t => BEATS.find(([s,e])=>t>=s&&t<=e) || BEATS[BEATS.length-1]
const getBeatProgress = t => { const [s,e]=getBeat(t); return Math.min(1,(t-s)/(e-s+1)) }

function Badge({id, results}) {
  const s = results[id]
  if (!s)                   return <span className="badge idle">Idle</span>
  if (s.status==='loading') return <span className="badge load">Testing…</span>
  if (s.status==='ok')      return <span className="badge ok">✓ Live</span>
  return <span className="badge err">✗ Error</span>
}

function ConfigModal({isOpen, onClose, onSave, onTest, testResults}) {
  const [agents, setAgents] = useState([
    {id:'Alex',  hidden_agenda:"Wants to convince Jamie to skip college and drive to Mexico. Secretly terrified of growing up.", model_config:{provider:'lm_studio',base_url:'http://localhost:1234/v1',model_name:'local-model',api_key:''}},
    {id:'Jamie', hidden_agenda:"Just realized the mysterious duffel bag in the back belongs to a dangerous cartel. Wants to get home immediately without panicking Alex.", model_config:{provider:'lm_studio',base_url:'http://localhost:1234/v1',model_name:'local-model',api_key:''}},
  ])
  if (!isOpen) return null

  const mutate = (i,f,v) => {
    const a = [...agents]
    if (['provider','model_name','base_url','api_key'].includes(f)) {
      a[i].model_config[f] = v
      if (f==='provider') {
        if (v==='lm_studio')  {a[i].model_config.base_url='http://localhost:1234/v1'; a[i].model_config.model_name='local-model'}
        if (v==='openrouter') {a[i].model_config.base_url='https://openrouter.ai/api/v1'; a[i].model_config.model_name='google/gemini-1.5-pro'}
        if (v==='google')     {a[i].model_config.base_url=''; a[i].model_config.model_name='gemini-1.5-pro-latest'}
      }
    } else a[i][f]=v
    setAgents(a)
  }

  return (
    <div className="overlay">
      <div className="modal">
        <div className="mtitle">🎭 Actor Roster & LLM Config</div>
        {agents.map((ag,i)=>(
          <div key={i} className="ccard">
            <div className="chead">
              <div style={{width:30,height:30,borderRadius:'50%',background:cc(i),display:'flex',alignItems:'center',justifyContent:'center',fontSize:11,fontWeight:800,color:'#fff',fontFamily:'JetBrains Mono,monospace',flexShrink:0}}>
                {ag.id.substring(0,2).toUpperCase()}
              </div>
              <input type="text" value={ag.id} onChange={e=>mutate(i,'id',e.target.value)} placeholder="Name" style={{flex:1,marginBottom:0}}/>
              <button className="btn-test" onClick={()=>onTest(ag.id,ag.model_config)}>Test</button>
              <Badge id={ag.id} results={testResults}/>
            </div>
            {testResults[ag.id]?.status==='error' && <div style={{fontSize:12,color:'#fc8181',padding:'6px 10px',background:'rgba(252,129,129,.08)',borderRadius:6,marginBottom:8}}>{testResults[ag.id].message}</div>}
            <input type="text"     value={ag.hidden_agenda}               onChange={e=>mutate(i,'hidden_agenda',e.target.value)} placeholder="🕵 Hidden agenda (the AI uses this secretly)"/>
            <div className="crow2">
              <select value={ag.model_config.provider} onChange={e=>mutate(i,'provider',e.target.value)} style={{flex:'0 0 155px'}}>
                <option value="lm_studio">LM Studio (Local)</option>
                <option value="openrouter">OpenRouter (Cloud)</option>
                <option value="google">Google GenAI</option>
              </select>
              <input type="text" value={ag.model_config.model_name} onChange={e=>mutate(i,'model_name',e.target.value)} placeholder="Model name"/>
            </div>
            <input type="password" value={ag.model_config.api_key} onChange={e=>mutate(i,'api_key',e.target.value)} placeholder="API Key (leave blank for LM Studio)"/>
          </div>
        ))}
        <button className="btn-add" onClick={()=>setAgents([...agents,{id:`Character_${agents.length+1}`,hidden_agenda:'',model_config:{provider:'lm_studio',base_url:'http://localhost:1234/v1',model_name:'local-model',api_key:''}}])}>+ Add Character</button>
        <div className="mfoot">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-pri" onClick={()=>onSave(agents)}>Save & Apply</button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [msgs,    setMsgs]    = useState([{type:'action',content:'[SYSTEM]: Ready — press ▶ Start Scene to begin.'}])
  const [monos,   setMonos]   = useState([])
  const [vitals,  setVitals]  = useState({tension:.5, turn_count:0})
  const [world,   setWorld]   = useState({location:'Unknown',lighting:'Unknown',props:[]})
  const [agents,  setAgents]  = useState([])
  const [cmd,     setCmd]     = useState('')
  const [loc,     setLoc]     = useState('')
  const [auto,    setAuto]    = useState(false)
  const [tts,     setTts]     = useState(false)
  const [wsOk,    setWsOk]    = useState(false)
  const [cfgOpen, setCfgOpen] = useState(false)
  const [testRes, setTestRes] = useState({})
  const [tab,     setTab]     = useState('vitals')  // 'vitals' | 'thoughts'

  const wsRef   = useRef(null)
  const feedRef = useRef(null)
  const monoRef = useRef(null)
  const autoRef = useRef(false)
  const ttsRef  = useRef(false)
  const timerRef= useRef(null)

  useEffect(()=>{autoRef.current=auto},[auto])
  useEffect(()=>{ttsRef.current=tts},[tts])

  const speak = (text,name='') => {
    if (!ttsRef.current||!('speechSynthesis' in window)) return
    const u = new SpeechSynthesisUtterance(text.replace(/\[.*?\]/g,'').trim())
    u.pitch = .8+((name.charCodeAt(0)||65)%8)/18
    speechSynthesis.speak(u)
  }

  useEffect(()=>{
    const sock = new WebSocket('ws://localhost:8000/ws')
    wsRef.current = sock
    sock.onopen  = () => { setWsOk(true); sock.send(JSON.stringify({type:'get_state'})) }
    sock.onclose = () => setWsOk(false)
    sock.onerror = () => setWsOk(false)
    sock.onmessage = ev => {
      const d = JSON.parse(ev.data)
      if (d.type==='dialogue'||d.type==='action') {
        setMsgs(p=>[...p,d])
        if (d.type==='dialogue') speak(d.content, d.agent_id||'')
      } else if (d.type==='monologue') {
        setMonos(p=>[...p,d])
        setTab('thoughts')
      } else if (d.type==='world_update') {
        setWorld(d.world)
      } else if (d.type==='agents_update') {
        setAgents(d.agents)
      } else if (d.type==='image_update') {
        setMsgs(p=>[...p,{type:'image',url:d.url,prompt:d.prompt}])
      } else if (d.type==='history_reset') {
        setMsgs(d.messages||[]); setMonos(d.monologues||[])
      } else if (d.type==='vitals_update') {
        setVitals(d.vitals)
        if (autoRef.current) {
          if (timerRef.current) clearTimeout(timerRef.current)
          timerRef.current = setTimeout(()=>{
            if (autoRef.current && wsRef.current?.readyState===1)
              wsRef.current.send(JSON.stringify({type:'next_turn'}))
            timerRef.current=null
          }, 3200)
        }
      } else if (d.type==='check_result') {
        setTestRes(p=>({...p,[d.agent_id]:d}))
      }
    }
    return ()=>sock.close()
  },[])

  useEffect(()=>{ if(feedRef.current) feedRef.current.scrollTop=feedRef.current.scrollHeight },[msgs])
  useEffect(()=>{ if(monoRef.current) monoRef.current.scrollTop=monoRef.current.scrollHeight },[monos])

  const send = o => wsRef.current?.readyState===1 && wsRef.current.send(JSON.stringify(o))
  const lastSpk = [...msgs].reverse().find(m=>m.agent_id)?.agent_id

  const turnCount = vitals.turn_count ?? 0
  const beat = getBeat(turnCount)
  const beatProgress = getBeatProgress(turnCount)

  const renderMsg = (m,i) => {
    if (m.type==='image') return (
      <div key={i} style={{animation:'up .3s ease-out'}}>
        <div style={{fontSize:11,color:'var(--t4)',marginBottom:6,fontStyle:'italic'}}>🎬 {m.prompt?.substring(0,90)}…</div>
        <img src={m.url} alt="" style={{width:'100%',borderRadius:10,border:'1px solid var(--border)'}}/>
      </div>
    )
    if (m.type==='dialogue' && m.agent_id) {
      const idx = agents.findIndex(a=>a.id===m.agent_id)
      const col = cc(idx>=0?idx:0)
      return (
        <div key={i} className="msg-d">
          <div className="avsm" style={{background:col}}>{m.agent_id.substring(0,2).toUpperCase()}</div>
          <div className="mbody">
            <div className="mname" style={{color:col}}>{m.agent_id}</div>
            <div className="mtext">{m.content.replace(/^[^:]+:\s*/,'')}</div>
          </div>
        </div>
      )
    }
    const isDir = m.content?.includes('[DIRECTOR')
    const isSys = m.content?.includes('[SYSTEM')||m.content?.includes('[SCENE START')
    const isScn = m.content?.includes('[SCENE CHANGE')
    const isErr = m.content?.includes('[ERROR')
    return <div key={i} className={`msg-a${isDir?' dir':isSys?' sys':isScn?' scn':isErr?' err':''}`}>{m.content}</div>
  }

  return (
    <div className="shell">
      <ConfigModal isOpen={cfgOpen} onClose={()=>setCfgOpen(false)}
        onSave={a=>{send({type:'configure_scene',agents:a});setCfgOpen(false)}}
        onTest={(id,cfg)=>{setTestRes(p=>({...p,[id]:{status:'loading'}}));send({type:'check_model',agent_id:id,model_config:cfg})}}
        testResults={testRes}/>

      {/* ── Topbar ── */}
      <div className="topbar">
        <div className="logo">
          <div className="logo-gem">🎭</div>
          <div className="logo-text">
            <div className="name">Persona<em>Play</em> Pro</div>
            <div className="sub">Multi-Agent Theater Engine</div>
          </div>
        </div>
        <div className="tsep"/>

        <div className="ctrl-group">
          <button className="cb green" onClick={()=>send({type:'start_scene'})}>▶ Start Scene</button>
          <button className="cb"       onClick={()=>{setAuto(false);setMsgs(p=>[...p,{type:'action',content:'[SYSTEM]: ⏸ Paused.'}])}}>⏸ Pause</button>
          <button className="cb red"   onClick={()=>{setAuto(false);send({type:'stop_scene'})}}>⏹ Stop</button>
        </div>
        <div className="tsep"/>
        <div className="ctrl-group">
          <button className="cb purple" onClick={()=>send({type:'next_turn'})}>⚡ Next Turn</button>
          <button className="cb cyan"   onClick={()=>send({type:'rewind_turns',turns:3})}>⏪ Rewind</button>
          <button className="cb amber"  onClick={()=>send({type:'export_script'})}>⬇ Export</button>
        </div>

        <div className="tb-right">
          <div className="turn-badge">Turn {turnCount}</div>
          <div className="ws-badge">
            <div className={`wdot ${wsOk?'on':'off'}`}/>
            {wsOk ? 'Connected' : 'Offline'}
          </div>
          <button className="cb" style={{borderColor:'rgba(167,139,250,.4)',color:'var(--purple)',background:'rgba(167,139,250,.1)'}}
            onClick={()=>setCfgOpen(true)}>⚙ Configure</button>
        </div>
      </div>

      {/* ── Beat bar ── */}
      <div className="beatbar">
        <span className="beat-label">Narrative</span>
        <span className="beat-name">{beat[2]}</span>
        <div className="beat-track"><div className="beat-fill" style={{width:`${beatProgress*100}%`}}/></div>
        <span className="beat-desc">Turn {turnCount} of {beat[1]}</span>
      </div>

      {/* ── Dashboard ── */}
      <div className="dash">

        {/* ── LEFT: Director ── */}
        <div className="panel">
          <div className="ph">
            <div className="ph-icon" style={{background:'rgba(167,139,250,.18)'}}>🎬</div>
            <span className="ph-title">Director</span>
          </div>
          <div className="pb">
            <div className="togrow">
              <span className="togl">🎞 Auto-Play</span>
              <label className="sw"><input type="checkbox" checked={auto} onChange={e=>setAuto(e.target.checked)}/><span className="sw-t"/></label>
            </div>
            <div className="togrow">
              <span className="togl">🔊 Voice (TTS)</span>
              <label className="sw"><input type="checkbox" checked={tts} onChange={e=>setTts(e.target.checked)}/><span className="sw-t"/></label>
            </div>

            <div className="rule"/>
            <div className="sec">🌍 World State</div>
            <div className="wcard">
              <div className="wrow"><span className="wl">📍 Location</span><span className="wv">{world.location}</span></div>
              <div className="wrow"><span className="wl">💡 Lighting</span><span className="wv">{world.lighting}</span></div>
              <div style={{display:'flex',flexDirection:'column',gap:6}}>
                <div style={{display:'flex',justifyContent:'space-between'}}>
                  <span className="wl">🔥 Scene Tension</span>
                  <span style={{fontSize:13,fontWeight:800,color:'var(--amber)'}}>{Math.round((vitals.tension||.5)*100)}%</span>
                </div>
                <div className="tension-track"><div className="tension-fill" style={{width:`${(vitals.tension||.5)*100}%`}}/></div>
                <input type="range" min="0" max="1" step="0.05" value={vitals.tension||.5}
                  onChange={e=>send({type:'force_scene_tension',value:parseFloat(e.target.value)})}
                  style={{accentColor:'var(--amber)'}}/>
              </div>
            </div>

            {world.props.length>0 && <>
              <div className="sec">🎒 Props</div>
              {world.props.map(p=>(
                <div key={p.id} className="prop-row">
                  <span className="pname">{p.id.replace(/_/g,' ')}</span>
                  <select className="psel" value={p.owner} onChange={e=>send({type:'force_give_prop',prop_id:p.id,owner:e.target.value})}>
                    <option value="Nobody">Nobody</option>
                    {agents.map(a=><option key={a.id} value={a.id}>{a.id}</option>)}
                  </select>
                </div>
              ))}
            </>}

            <div className="rule"/>
            <div className="sec">🚀 Teleport Scene</div>
            <form style={{display:'flex',gap:6}} onSubmit={e=>{e.preventDefault();if(loc.trim()){send({type:'change_scene',location:loc});setLoc('')}}}>
              <input type="text" placeholder="New location…" value={loc} onChange={e=>setLoc(e.target.value)} style={{flex:1}}/>
              <button type="submit" className="btn-go">Go</button>
            </form>

            <div className="sec">⚡ Inject Chaos</div>
            <form style={{display:'flex',flexDirection:'column',gap:8}} onSubmit={e=>{e.preventDefault();if(cmd.trim()){send({type:'director_command',command:cmd});setMsgs(p=>[...p,{type:'action',content:`[DIRECTOR INJECTS]: ${cmd}`}]);setCmd('')}}}>
              <input type="text" placeholder="E.g. 'Police appear in the rear view'" value={cmd} onChange={e=>setCmd(e.target.value)}/>
              <button type="submit" className="btn-chaos">🔥 Inject into Scene</button>
            </form>
          </div>
        </div>

        {/* ── CENTER: Theater ── */}
        <div className="panel">
          <div className="ph">
            <div className="ph-icon" style={{background:'rgba(103,232,249,.12)'}}>🎭</div>
            <span className="ph-title">Theater</span>
            <span className="ph-sub">{world.location}</span>
          </div>

          <div className="stage">
            <div className="stage-spotlight"/>
            <div className="slabel">Stage</div>
            {agents.map((ag,i)=>{
              const col=cc(i)
              const left=18+((i*45)%58)+(ag.emotions?.energy??0.5)*12
              const top=22+((i*22)%34)+(ag.emotions?.tension??0.5)*14
              return (
                <div key={ag.id} className={`avatar${lastSpk===ag.id?' speaking':''}`}
                  style={{left:`${left}%`,top:`${top}%`,background:col}}>
                  {ag.id.substring(0,2).toUpperCase()}
                  <span className="atag">{ag.id}</span>
                </div>
              )
            })}
            <div className="stage-floor"/>
          </div>

          <div className="feed" ref={feedRef}>
            {msgs.map((m,i)=>renderMsg(m,i))}
          </div>
        </div>

        {/* ── RIGHT: Backstage ── */}
        <div className="panel">
          <div className="ph">
            <div className="ph-icon" style={{background:'rgba(249,168,212,.12)'}}>🧠</div>
            <span className="ph-title">Backstage</span>
          </div>
          <div className="tabs">
            <button className={`tab${tab==='vitals'?' active':''}`} onClick={()=>setTab('vitals')}>⚡ Vitals</button>
            <button className={`tab${tab==='thoughts'?' active':''}`} onClick={()=>setTab('thoughts')}>💭 Thoughts {monos.length>0&&<span style={{marginLeft:4,fontSize:10,background:'rgba(167,139,250,.2)',color:'var(--purple)',borderRadius:4,padding:'1px 5px'}}>{monos.length}</span>}</button>
          </div>

          {tab==='vitals' && (
            <div className="pb">
              {agents.map((ag,i)=>{
                const col=cc(i)
                return (
                  <div key={ag.id} className="vcard">
                    <div className="vname">
                      <div className="vdot" style={{background:col}}>{ag.id.substring(0,2).toUpperCase()}</div>
                      {ag.id}
                      {lastSpk===ag.id&&<span className="spk-badge">LIVE</span>}
                    </div>
                    {[['tension','🔥','#fc8181'],['energy','⚡','#4ade80'],['affection','💜','#f9a8d4'],['suspicion','👁','#fcd34d']].map(([s,ic,c])=>(
                      <div key={s} className="vrow">
                        <span className="vlbl" style={{color:c}}>{ic} {s.charAt(0).toUpperCase()+s.slice(1)}</span>
                        <input type="range" min="0" max="1" step="0.05"
                          value={ag.emotions?.[s]??0.5}
                          onChange={e=>send({type:'force_emotion',agent_id:ag.id,emotion:s,value:parseFloat(e.target.value)})}
                          style={{flex:1,accentColor:c}}/>
                        <span className="vpct">{Math.round((ag.emotions?.[s]??0.5)*100)}%</span>
                      </div>
                    ))}
                  </div>
                )
              })}
              {agents.length===0&&<div className="mempty">No agents loaded yet.<br/>Press Configure to set up your cast.</div>}
            </div>
          )}

          {tab==='thoughts' && (
            <div className="pb">
              <div className="mono-stream" ref={monoRef}>
                {monos.length===0&&<div className="mempty">Inner thoughts appear here<br/>as the scene unfolds…</div>}
                {monos.map((m,i)=>{
                  const idx=agents.findIndex(a=>a.id===m.agent_id)
                  const col=cc(idx>=0?idx:0)
                  return (
                    <div key={i} className="mcard" style={{borderLeftColor:col}}>
                      <div className="mwho" style={{color:col}}>{m.agent_id}</div>
                      <div className="mtext">{m.content}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
