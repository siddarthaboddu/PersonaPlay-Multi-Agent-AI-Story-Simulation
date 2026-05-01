import { useState, useEffect, useRef } from 'react'

function ConfigModal({ isOpen, onClose, onSave, onTest, testResults }) {
  const [agents, setAgents] = useState([
    {
      id: "Alex",
      hidden_agenda: "Wants to convince Jamie to skip college and drive to Mexico. Secretly terrified of growing up.",
      model_config: { provider: "lm_studio", base_url: "http://localhost:1234/v1", model_name: "local-model", api_key: "" }
    },
    {
      id: "Jamie",
      hidden_agenda: "Just realized the mysterious duffel bag in the back belongs to a dangerous cartel. Wants to get home immediately without panicking Alex.",
      model_config: { provider: "lm_studio", base_url: "http://localhost:1234/v1", model_name: "local-model", api_key: "" }
    }
  ]);

  if (!isOpen) return null;

  const handleAgentChange = (index, field, value) => {
    const newAgents = [...agents];
    if (field === 'model_config.provider') {
      newAgents[index].model_config.provider = value;
      if (value === 'lm_studio') {
        newAgents[index].model_config.base_url = "http://localhost:1234/v1";
        newAgents[index].model_config.model_name = "local-model";
      } else if (value === 'openrouter') {
        newAgents[index].model_config.base_url = "https://openrouter.ai/api/v1";
        newAgents[index].model_config.model_name = "google/gemini-1.5-pro";
      } else if (value === 'google') {
        newAgents[index].model_config.base_url = "";
        newAgents[index].model_config.model_name = "gemini-1.5-pro-latest";
      }
    } else if (field.startsWith('model_config.')) {
      const configField = field.split('.')[1];
      newAgents[index].model_config[configField] = value;
    } else {
      newAgents[index][field] = value;
    }
    setAgents(newAgents);
  };

  const addAgent = () => {
    setAgents([...agents, {
      id: `Character_${agents.length + 1}`,
      hidden_agenda: "",
      model_config: { provider: "lm_studio", base_url: "http://localhost:1234/v1", model_name: "local-model", api_key: "" }
    }]);
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2 className="panel-header">Actor Roster Configuration</h2>
        
        {agents.map((agent, i) => (
          <div key={i} className="character-card">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
              <input 
                type="text" 
                placeholder="Name" 
                value={agent.id} 
                onChange={e => handleAgentChange(i, 'id', e.target.value)} 
                style={{margin: 0, flex: 1}}
              />
              <button 
                onClick={() => onTest(agent.id, agent.model_config)}
                style={{marginLeft: '8px', padding: '4px 12px', fontSize: '12px', background: testResults[agent.id]?.status === 'ok' ? '#22c55e' : (testResults[agent.id]?.status === 'error' ? '#ef4444' : '#6366f1')}}
              >
                {testResults[agent.id]?.status === 'loading' ? 'Testing...' : (testResults[agent.id]?.status === 'ok' ? 'OK' : 'Test')}
              </button>
            </div>
            
            {testResults[agent.id]?.status === 'error' && (
              <div style={{color: '#ef4444', fontSize: '10px', marginBottom: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                {testResults[agent.id].message}
              </div>
            )}

            <input 
              type="text" 
              placeholder="Hidden Agenda" 
              value={agent.hidden_agenda} 
              onChange={e => handleAgentChange(i, 'hidden_agenda', e.target.value)} 
            />
            
            <div style={{display: 'flex', gap: '8px', marginBottom: '8px'}}>
              <select 
                value={agent.model_config.provider} 
                onChange={e => handleAgentChange(i, 'model_config.provider', e.target.value)}
                style={{flex: 1, padding: '8px', background: 'rgba(0,0,0,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px'}}
              >
                <option value="lm_studio">LM Studio (Local)</option>
                <option value="openrouter">OpenRouter (Cloud)</option>
                <option value="google">Google GenAI (Native)</option>
              </select>
              <input 
                type="text" 
                placeholder="Model Name" 
                value={agent.model_config.model_name} 
                onChange={e => handleAgentChange(i, 'model_config.model_name', e.target.value)} 
                style={{flex: 1}}
              />
            </div>
            
            <input 
              type="password" 
              placeholder="API Key (Optional)" 
              value={agent.model_config.api_key} 
              onChange={e => handleAgentChange(i, 'model_config.api_key', e.target.value)} 
            />
          </div>
        ))}
        
        <button onClick={addAgent} style={{background: 'rgba(255,255,255,0.1)', width: '100%'}}>+ Add Character</button>
        
        <div className="modal-actions">
          <button onClick={onClose} style={{background: 'transparent', border: '1px solid rgba(255,255,255,0.2)'}}>Cancel</button>
          <button onClick={() => onSave(agents)}>Save & Apply</button>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [messages, setMessages] = useState([{ content: "[SYSTEM]: Ready to begin simulation...", type: "action" }]);
  const [monologues, setMonologues] = useState([]);
  const [vitals, setVitals] = useState({ tension: 0.5, energy: 0.8 });
  const [command, setCommand] = useState("");
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [testResults, setTestResults] = useState({});
  const [isAutoPlay, setIsAutoPlay] = useState(false);
  const [worldState, setWorldState] = useState({ location: "Unknown", lighting: "Unknown", props: [] });
  const [agentsStatus, setAgentsStatus] = useState([]);
  const [isTTSEnabled, setIsTTSEnabled] = useState(false);
  const [sceneInput, setSceneInput] = useState("");
  
  const wsRef = useRef(null);
  const scriptRef = useRef(null);
  const monoRef = useRef(null);
  const autoPlayRef = useRef(isAutoPlay);
  const ttsRef = useRef(isTTSEnabled);

  useEffect(() => {
    autoPlayRef.current = isAutoPlay;
  }, [isAutoPlay]);

  useEffect(() => {
    ttsRef.current = isTTSEnabled;
  }, [isTTSEnabled]);

  const speakText = (text, characterName) => {
    if (!('speechSynthesis' in window) || !ttsRef.current) return;
    const cleanText = text.replace(/\[.*?\]/g, '').trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const hash = characterName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    utterance.pitch = 0.8 + ((hash % 10) / 20); // 0.8 to 1.3
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  useEffect(() => {
    wsRef.current = new WebSocket("ws://localhost:8000/ws");
    
    wsRef.current.onopen = () => {
        wsRef.current.send(JSON.stringify({ type: "get_state" }));
    };
    
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "dialogue" || data.type === "action") {
        setMessages(prev => [...prev, data]);
        if (data.type === "dialogue") {
            speakText(data.content, data.agent_id || "Unknown");
        }
      } else if (data.type === "monologue") {
        setMonologues(prev => [...prev, data]);
      } else if (data.type === "world_update") {
        setWorldState(data.world);
      } else if (data.type === "agents_update") {
        setAgentsStatus(data.agents);
      } else if (data.type === "image_update") {
        setMessages(prev => [...prev, { type: "image", url: data.url, prompt: data.prompt }]);
      } else if (data.type === "history_reset") {
        setMessages(data.messages);
        setMonologues(data.monologues);
      } else if (data.type === "vitals_update") {
        setVitals(data.vitals);
        
        // Auto-play logic: trigger next turn after a short delay if enabled
        if (autoPlayRef.current) {
          setTimeout(() => {
             if (autoPlayRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                 wsRef.current.send(JSON.stringify({ type: "next_turn" }));
             }
          }, 3000);
        }
      } else if (data.type === "check_result") {
        setTestResults(prev => ({...prev, [data.agent_id]: data}));
      }
    };

    return () => wsRef.current?.close();
  }, []);

  useEffect(() => {
    if (scriptRef.current) scriptRef.current.scrollTop = scriptRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (monoRef.current) monoRef.current.scrollTop = monoRef.current.scrollHeight;
  }, [monologues]);

  const sendCommand = (e) => {
    e.preventDefault();
    if (!command.trim()) return;
    wsRef.current.send(JSON.stringify({ type: "director_command", command }));
    setMessages(prev => [...prev, { type: "action", content: `[DIRECTOR INJECTS]: ${command}` }]);
    setCommand("");
  };

  const handleSceneChange = (e) => {
    e.preventDefault();
    if (!sceneInput.trim()) return;
    wsRef.current.send(JSON.stringify({ type: "change_scene", location: sceneInput }));
    setSceneInput("");
  };

  const startScene = () => {
    wsRef.current.send(JSON.stringify({ type: "start_scene" }));
  };

  const nextTurn = () => {
    wsRef.current.send(JSON.stringify({ type: "next_turn" }));
  };

  const stopScene = () => {
    setIsAutoPlay(false);
    wsRef.current.send(JSON.stringify({ type: "stop_scene" }));
  };

  const pauseScene = () => {
    setIsAutoPlay(false);
    setMessages(prev => [...prev, { type: "action", content: "[SYSTEM]: ⏸️ Auto-play paused. Current turn will finish." }]);
  };

  const exportScript = () => {
    wsRef.current.send(JSON.stringify({ type: "export_script" }));
  };

  const handleConfigSave = (agents) => {
    wsRef.current.send(JSON.stringify({ type: "configure_scene", agents }));
    setIsConfigOpen(false);
  };

  const handleTestConnection = (agentId, modelConfig) => {
    setTestResults(prev => ({...prev, [agentId]: { status: 'loading' }}));
    wsRef.current.send(JSON.stringify({ type: "check_model", agent_id: agentId, model_config: modelConfig }));
  };

  return (
    <div className="dashboard">
      <ConfigModal 
        isOpen={isConfigOpen} 
        onClose={() => setIsConfigOpen(false)} 
        onSave={handleConfigSave}
        onTest={handleTestConnection}
        testResults={testResults}
      />

      {/* Left Panel */}
      <div className="panel controller-panel">
        <div className="panel-header">World Controller</div>
        <div className="controls">
          <button onClick={() => setIsConfigOpen(true)} style={{background: '#6366f1'}}>Configure Actors</button>
          <hr style={{borderColor: 'rgba(255,255,255,0.1)', margin: '8px 0'}}/>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <button onClick={startScene} style={{ flex: 1 }}>Start</button>
            <button onClick={pauseScene} style={{ flex: 1, background: '#f59e0b' }}>Pause</button>
            <button onClick={stopScene} style={{ flex: 1, background: '#ef4444' }}>Stop</button>
          </div>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <button 
              onClick={nextTurn}
              style={{
                flex: 2,
                background: messages.length > 0 && messages[messages.length-1].content.includes("SCENE START") ? '#22c55e' : ''
              }}
            >
              Next Turn
            </button>
            <button onClick={() => wsRef.current.send(JSON.stringify({ type: "rewind_turns", turns: 3 }))} style={{flex: 1, background: '#6366f1', fontSize: '12px'}}>⏪ Rewind</button>
            <button onClick={exportScript} style={{flex: 1, background: '#f59e0b', fontSize: '12px'}}>Export</button>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', marginBottom: '8px' }}>
            <input 
              type="checkbox" 
              id="autoPlay" 
              checked={isAutoPlay} 
              onChange={e => setIsAutoPlay(e.target.checked)} 
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="autoPlay" style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px', cursor: 'pointer' }}>Auto-Play Scene</label>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', marginBottom: '8px' }}>
            <input 
              type="checkbox" 
              id="ttsEnable" 
              checked={isTTSEnabled} 
              onChange={e => setIsTTSEnabled(e.target.checked)} 
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="ttsEnable" style={{ color: 'rgba(255,255,255,0.8)', fontSize: '14px', cursor: 'pointer' }}>Enable TTS (Voice)</label>
          </div>
          
          {/* World State UI */}
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '8px', marginBottom: '8px', fontSize: '13px' }}>
             <div style={{fontWeight: 'bold', color: '#fbbf24', marginBottom: '4px'}}>Current World</div>
             <div><span style={{color: '#94a3b8'}}>Location:</span> {worldState.location}</div>
             <div><span style={{color: '#94a3b8'}}>Lighting:</span> {worldState.lighting}</div>
             <div style={{color: '#94a3b8', marginTop: '4px'}}>Props:</div>
             <ul style={{margin: '0 0 0 16px', padding: 0}}>
                {worldState.props.length === 0 ? <li style={{color: '#94a3b8'}}>None</li> : worldState.props.map(p => (
                   <li key={p.id} style={{display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px'}}>
                      <span style={{color: '#fde047'}}>{p.id.replace('_', ' ')}</span>
                      <select 
                        value={p.owner} 
                        onChange={e => wsRef.current.send(JSON.stringify({ type: "force_give_prop", prop_id: p.id, owner: e.target.value }))}
                        style={{marginLeft: 'auto', padding: '2px', fontSize: '10px', background: 'rgba(0,0,0,0.5)', color: 'white', border: 'none', borderRadius: '4px'}}
                      >
                        <option value="Nobody">Nobody</option>
                        {agentsStatus.map(a => <option key={a.id} value={a.id}>{a.id}</option>)}
                      </select>
                   </li>
                ))}
             </ul>
          </div>
          
          {agentsStatus.length > 0 && (
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '8px', marginBottom: '8px', fontSize: '13px' }}>
              <div style={{fontWeight: 'bold', color: '#38bdf8', marginBottom: '8px'}}>Sims Character Status</div>
              {agentsStatus.map((agent, i) => (
                <div key={i} style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#f8fafc', fontSize: '11px' }}>{agent.id}</strong>
                  {['tension', 'energy', 'affection', 'suspicion'].map(stat => (
                    <div key={stat} style={{ display: 'flex', alignItems: 'center', fontSize: '10px', marginBottom: '2px' }}>
                      <div style={{ width: '55px', textTransform: 'capitalize', color: '#cbd5e1' }}>{stat}</div>
                      <div style={{ flex: 1, background: '#1e293b', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ 
                          width: `${Math.max(0, Math.min(100, agent.emotions[stat] * 100))}%`, 
                          height: '100%', 
                          background: stat === 'energy' ? '#22c55e' : stat === 'tension' ? '#ef4444' : stat === 'affection' ? '#ec4899' : '#eab308',
                          transition: 'width 0.5s ease-in-out'
                        }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
          
          <form onSubmit={handleSceneChange} style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
             <input type="text" placeholder="New Location..." value={sceneInput} onChange={e => setSceneInput(e.target.value)} style={{flex: 1, padding: '6px', fontSize: '12px'}} />
             <button type="submit" style={{padding: '6px 10px', fontSize: '12px'}}>Move</button>
          </form>

          <form onSubmit={sendCommand} style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
            <input 
              type="text" 
              placeholder="Director Command..." 
              value={command} 
              onChange={e => setCommand(e.target.value)} 
            />
            <button type="submit">Inject Chaos</button>
          </form>
        </div>
      </div>

      {/* Center Panel */}
      <div className="panel theater-panel">
        <div className="panel-header">Theater View</div>
        
        {/* Animated Blocking 2D Stage */}
        <div style={{ height: '120px', background: '#0f172a', borderBottom: '1px solid rgba(255,255,255,0.1)', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: '10px', left: '10px', fontSize: '10px', color: '#64748b', letterSpacing: '2px', textTransform: 'uppercase' }}>STAGE: {worldState.location}</div>
          {agentsStatus.map((agent, i) => {
            const left = 20 + ((i * 35) % 60) + (agent.emotions.energy * 20);
            const top = 30 + ((i * 15) % 40) + (agent.emotions.tension * 20);
            return (
              <div key={agent.id} style={{ 
                position: 'absolute', 
                left: `${left}%`, 
                top: `${top}%`, 
                width: '32px', height: '32px', 
                borderRadius: '50%', background: '#3b82f6', 
                display: 'flex', alignItems: 'center', justifyContent: 'center', 
                fontSize: '12px', fontWeight: 'bold', color: 'white',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                transition: 'all 0.8s ease-in-out',
                border: messages.length > 0 && messages[messages.length-1].agent_id === agent.id ? '2px solid #fbbf24' : '2px solid transparent'
              }}>
                {agent.id.substring(0, 2).toUpperCase()}
              </div>
            );
          })}
        </div>

        <div className="script-feed" ref={scriptRef}>
          {messages.map((msg, i) => (
            <div key={i} className="script-line">
              {msg.type === "image" ? (
                <div style={{margin: '12px 0'}}>
                   <div style={{fontSize: '12px', color: '#94a3b8', fontStyle: 'italic', marginBottom: '4px'}}>🎬 Scene Render: {msg.prompt}</div>
                   <img src={msg.url} alt="Scene rendering" style={{width: '100%', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)'}} />
                </div>
              ) : (
                <>
                  {msg.agent_id && <span className="speaker">{msg.agent_id}: </span>}
                  <span>{msg.content}</span>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel */}
      <div className="panel backstage-panel">
        <div className="panel-header">Backstage</div>
        <div className="vitals">
          <div className="vital-bar">
            <span>Tension</span>
            <div className="progress-bg">
              <div className="progress-fill" style={{ width: `${vitals.tension * 100}%`, background: '#ef4444' }}></div>
            </div>
          </div>
          <div className="vital-bar">
            <span>Energy</span>
            <div className="progress-bg">
              <div className="progress-fill" style={{ width: `${vitals.energy * 100}%`, background: '#f59e0b' }}></div>
            </div>
          </div>
        </div>
        <div className="monologue-stream" ref={monoRef}>
          {monologues.map((msg, i) => (
            <div key={i}>[{msg.agent_id}]: {msg.content}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default App
