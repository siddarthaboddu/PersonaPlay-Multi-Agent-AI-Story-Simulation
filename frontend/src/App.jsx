import { useState, useEffect, useRef } from 'react'

function ConfigModal({ isOpen, onClose, onSave, onTest, testResults }) {
  const [agents, setAgents] = useState([
    {
      id: "Character_A",
      hidden_agenda: "Wants to steal the silver spoon",
      model_config: { provider: "lm_studio", base_url: "http://localhost:1234/v1", model_name: "local-model", api_key: "" }
    },
    {
      id: "Character_B",
      hidden_agenda: "Is deeply suspicious of everyone",
      model_config: { provider: "openrouter", base_url: "https://openrouter.ai/api/v1", model_name: "google/gemini-1.5-pro", api_key: "" }
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
            <button onClick={stopScene} style={{ flex: 1, background: '#ef4444' }}>Stop</button>
          </div>
          <button 
            onClick={nextTurn}
            style={{
              background: messages.length > 0 && messages[messages.length-1].content.includes("SCENE START") ? '#22c55e' : ''
            }}
          >
            Next Turn
          </button>
          
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
                   <li key={p.id}>{p.id} ({p.visibility}) - {p.owner}</li>
                ))}
             </ul>
          </div>
          
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
        <div className="script-feed" ref={scriptRef}>
          {messages.map((msg, i) => (
            <div key={i} className="script-line">
              {msg.agent_id && <span className="speaker">{msg.agent_id}: </span>}
              <span>{msg.content}</span>
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
