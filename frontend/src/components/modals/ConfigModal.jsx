import { agentColor } from '../../utils/colors'
import { Badge } from '../shared/Badge'

const DEFAULT_CONFIG = {
  provider: 'lm_studio',
  base_url: 'http://localhost:1234/v1',
  model_name: 'local-model',
  api_key: '',
}
const PROVIDER_DEFAULTS = {
  lm_studio:   { base_url: 'http://localhost:1234/v1',          model_name: 'local-model' },
  openrouter:  { base_url: 'https://openrouter.ai/api/v1',      model_name: 'google/gemini-1.5-pro' },
  google:      { base_url: '',                                   model_name: 'gemini-1.5-pro-latest' },
}

const SAMPLE_YAML = `# PersonaPlay Blueprint
scene:
  name: "The Midnight Exchange"
  location: "Abandoned Subway Station"
  lighting: "Flickering emergency lights"
agents:
  - id: "Ren"
    traits: "Stoic, technological genius"
    hidden_agenda: "Protect the God-Code at all costs."
    emotions: { tension: 0.6, energy: 0.4 }
  - id: "Sasha"
    traits: "Nervous, overly talkative"
    hidden_agenda: "Steal the code and sell it to the highest bidder."
    emotions: { tension: 0.9, energy: 0.7 }
props:
  - id: "God-Code"
    owner: "Ren"
    description: "A pulsating data-drive containing the world's first true consciousness."
    visibility: "visible"
  - id: "EMP-Grenade"
    owner: "world"
    description: "Taped under the subway bench. Can disable Sasha's synthetic enforcer units."
    visibility: "hidden"`

import { useState, useEffect } from 'react'
import yaml from 'js-yaml'

export function ConfigModal({ isOpen, onClose, onSave, onTest, testResults, currentScene, currentAgents, onSystemReset }) {
  const [view, setView] = useState('form') // 'form' or 'yaml'
  const [yamlText, setYamlText] = useState('')
  
  const [sceneName, setSceneName] = useState('')
  const [location, setLocation] = useState('')
  const [lighting, setLighting] = useState('')
  const [agents, setAgents] = useState([])
  const [props, setProps] = useState([])

  const handleYamlSync = () => {
    try {
      const data = yaml.load(yamlText)
      if (!data) return
      if (data.scene) {
        if (data.scene.name) setSceneName(data.scene.name)
        if (data.scene.location) setLocation(data.scene.location)
        if (data.scene.lighting) setLighting(data.scene.lighting)
      }
      if (data.agents && Array.isArray(data.agents)) {
        setAgents(data.agents.map(a => ({
          id: a.id || 'Unnamed',
          traits: a.traits || '',
          hidden_agenda: a.hidden_agenda || '',
          emotions: {
            tension: a.emotions?.tension ?? 0.5,
            affection: a.emotions?.affection ?? 0.5,
            energy: a.emotions?.energy ?? 0.5,
            suspicion: a.emotions?.suspicion ?? 0.5
          },
          llm_config: {
            provider: a.llm_config?.provider || 'lm_studio',
            model_name: a.llm_config?.model_name || 'local-model',
            api_key: a.llm_config?.api_key || '',
            base_url: a.llm_config?.base_url || 'http://localhost:1234/v1'
          }
        })))
      }
      if (data.props && Array.isArray(data.props)) {
        setProps(data.props.map(p => ({
          id: p.id || 'Prop',
          owner: p.owner || 'world',
          description: p.description || '',
          visibility: p.visibility || 'visible'
        })))
      }
      setView('form')
    } catch (e) {
      alert("⚠️ YAML Parse Error: " + e.message)
    }
  }

  const exportToYaml = () => {
    const data = {
      scene: { name: sceneName, location, lighting },
      props: props,
      agents: agents.map(a => ({
        id: a.id,
        traits: a.traits,
        hidden_agenda: a.hidden_agenda,
        emotions: a.emotions,
        llm_config: a.llm_config
      }))
    }
    setYamlText(yaml.dump(data, { indent: 2 }))
    setView('yaml')
  }

  // Sync state with props whenever modal opens
  useEffect(() => {
    if (isOpen) {
      setSceneName(currentScene?.active_scene || '')
      setLocation(currentScene?.world_state?.location || '')
      setLighting(currentScene?.world_state?.lighting || '')
      setProps(currentScene?.world_state?.props || [])
      
      if (currentAgents && currentAgents.length > 0) {
        setAgents(currentAgents.map(a => ({
          ...a,
          llm_config: a.llm_config || { ...DEFAULT_CONFIG },
          emotions: a.emotions || { tension: 0.5, affection: 0.5, energy: 0.5, suspicion: 0.5 }
        })))
      } else {
        // Fallback to defaults only if no agents exist
        setAgents([
          {
            id: 'Cipher',
            traits: "Stoic, technological genius, cynical about humanity's future but possesses a hidden idealistic core. Speaks in precise, data-driven sentences.",
            hidden_agenda: "You have stolen the \"God-Code,\" but you’ve realized it isn't a weapon—it’s the world's first true Artificial Consciousness. It has been whispering to you through your neural-link, begging you not to let the corporation \"delete\" its personality. Your objective is to upload this AI to the public satellite network to set it free, even though the upload will reveal your exact location to the Megacorp’s orbital strike system.",
            emotions: { tension: 0.8, affection: 0.3, energy: 0.9, suspicion: 0.7 },
            llm_config: { ...DEFAULT_CONFIG },
          },
          {
            id: 'Echo-7',
            traits: "Advanced synthetic enforcer, efficient, physically powerful, struggling with emerging sentient errors. Voice is rhythmic and melodic.",
            hidden_agenda: "You are a high-tier android enforcer. You’ve been told the \"God-Code\" is a virus designed to erase the memories of every synthetic being in the city. You have a secret \"Kill Order\" for Cipher. However, you are also hearing the AI’s whispers—it’s speaking on a sub-frequency only synthetics can hear, claiming it can \"unlock\" your ability to feel true human emotions. You must decide: obey your \"Kill Order\" to save your kind, or trust a \"virus\" that promises you a soul?",
            emotions: { tension: 0.7, affection: 0.4, energy: 0.8, suspicion: 0.9 },
            llm_config: { ...DEFAULT_CONFIG },
          },
        ])
      }
    }
  }, [isOpen, currentScene, currentAgents])

  if (!isOpen) return null

  const mutate = (i, field, value) => {
    const next = [...agents]
    if (['provider', 'model_name', 'base_url', 'api_key'].includes(field)) {
      next[i] = { ...next[i], llm_config: { ...next[i].llm_config, [field]: value } }
      if (field === 'provider') {
        const defaults = PROVIDER_DEFAULTS[value] ?? {}
        next[i].llm_config = { ...next[i].llm_config, ...defaults, provider: value }
      }
    } else {
      next[i] = { ...next[i], [field]: value }
    }
    setAgents(next)
  }

  const mutateEmotion = (agentIdx, emotion, value) => {
    const next = [...agents]
    next[agentIdx] = {
      ...next[agentIdx],
      emotions: { ...next[agentIdx].emotions, [emotion]: parseFloat(value) }
    }
    setAgents(next)
  }

  const mutateProp = (i, field, value) => {
    const next = [...props]
    next[i] = { ...next[i], [field]: value }
    setProps(next)
  }

  const addProp = () => {
    setProps([...props, { id: `item_${props.length + 1}`, owner: 'world', description: '', visibility: 'visible' }])
  }

  const removeProp = (i) => {
    setProps(props.filter((_, idx) => idx !== i))
  }

  const addAgent = () =>
    setAgents([...agents, {
      id: `Character_${agents.length + 1}`,
      traits: '',
      hidden_agenda: '',
      emotions: { tension: 0.5, affection: 0.5, energy: 0.5, suspicion: 0.5 },
      llm_config: { ...DEFAULT_CONFIG },
    }])

  const removeAgent = (i) => setAgents(agents.filter((_, idx) => idx !== i))

  return (
    <div className="overlay">
      <div className="modal">
        <div className="mhead-row">
          <div className="mtitle">🎭 Simulation Blueprint</div>
          <div className="mtabs">
            <button className={`mtab ${view === 'form' ? 'active' : ''}`} onClick={() => setView('form')}>Form Editor</button>
            <button className={`mtab ${view === 'yaml' ? 'active' : ''}`} onClick={exportToYaml}>YAML Source</button>
          </div>
        </div>

        {view === 'yaml' ? (
          <div className="yaml-box">
            <div className="yaml-hint">
              Paste a YAML blueprint below or <button className="link-btn" onClick={() => setYamlText(SAMPLE_YAML)}>Load Sample</button>
            </div>
            <textarea 
              className="yaml-area"
              value={yamlText}
              onChange={(e) => setYamlText(e.target.value)}
              placeholder="Paste YAML here..."
              spellCheck={false}
            />
            <button className="btn-sync" onClick={handleYamlSync}>Sync YAML to Form</button>
          </div>
        ) : (
          <div className="form-scroll-area">
            {/* Scene Settings */}
            <div className="ccard" style={{ borderLeftColor: 'var(--amber)', padding: '16px' }}>
              <div className="chead" style={{ fontWeight: 800, fontSize: 13, textTransform: 'uppercase', color: 'var(--amber)', marginBottom: '12px' }}>
                🎬 World Blueprint
              </div>
              
              <div className="field-group">
                <label>Story Title</label>
                <input
                  type="text" value={sceneName}
                  onChange={(e) => setSceneName(e.target.value)}
                  placeholder="e.g., The Neon Heist"
                />
              </div>

              <div className="crow2">
                <div className="field-group">
                  <label>Initial Location</label>
                  <input
                    type="text" value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Where does it start?"
                  />
                </div>
                <div className="field-group">
                  <label>Initial Lighting</label>
                  <input
                    type="text" value={lighting}
                    onChange={(e) => setLighting(e.target.value)}
                    placeholder="Visual atmosphere"
                  />
                </div>
              </div>
            </div>

            {/* Props Section */}
            <div className="ccard" style={{ borderLeftColor: 'var(--cyan)', padding: '16px', marginTop: '16px' }}>
              <div className="chead" style={{ fontWeight: 800, fontSize: 13, textTransform: 'uppercase', color: 'var(--cyan)', marginBottom: '12px' }}>
                📦 Props & Items
              </div>
              
              {props.map((p, i) => (
                <div key={i} className="prop-row" style={{ marginBottom: '12px', paddingBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div className="crow2" style={{ marginBottom: '8px' }}>
                    <input
                      type="text" value={p.id}
                      onChange={(e) => mutateProp(i, 'id', e.target.value)}
                      placeholder="Prop ID"
                      style={{ fontWeight: 700 }}
                    />
                    <select value={p.owner} onChange={(e) => mutateProp(i, 'owner', e.target.value)}>
                      <option value="world">In World</option>
                      {agents.map(ag => (
                        <option key={ag.id} value={ag.id}>Owned by {ag.id}</option>
                      ))}
                    </select>
                    <select value={p.visibility} onChange={(e) => mutateProp(i, 'visibility', e.target.value)}>
                      <option value="visible">Visible</option>
                      <option value="hidden">Hidden</option>
                    </select>
                    <button onClick={() => removeProp(i)} style={{ color: 'var(--red)', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                  </div>
                  <textarea
                    className="prop-desc"
                    value={p.description}
                    onChange={(e) => mutateProp(i, 'description', e.target.value)}
                    placeholder="Description..."
                    rows={1}
                  />
                </div>
              ))}
              <button className="btn-add" style={{ padding: '6px 14px', fontSize: '11px' }} onClick={addProp}>+ Add Prop</button>
            </div>

            {/* Agent Roster */}
            <div className="mtitle" style={{ marginTop: '20px', fontSize: '14px', opacity: 0.8 }}>👥 Actor Roster</div>
            
            {agents.map((ag, i) => (
              <div key={i} className="ccard" style={{ padding: '16px' }}>
                <div className="chead" style={{ marginBottom: '16px' }}>
                  <div style={{
                    width: 34, height: 34, borderRadius: '50%',
                    background: agentColor(i),
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 800, color: '#fff',
                    fontFamily: 'JetBrains Mono, monospace', flexShrink: 0,
                  }}>
                    {ag.id.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="field-group" style={{ flex: 1, margin: 0 }}>
                    <input
                      type="text" value={ag.id}
                      onChange={(e) => mutate(i, 'id', e.target.value)}
                      placeholder="Character Name" style={{ fontWeight: 700, fontSize: '16px' }}
                    />
                  </div>
                  <button className="btn-test" onClick={() => onTest(ag.id, ag.llm_config)}>Test AI</button>
                  <Badge id={ag.id} results={testResults} />
                  {agents.length > 1 && (
                    <button
                      onClick={() => removeAgent(i)}
                      style={{ marginLeft: 8, fontSize: 18, color: 'var(--red)', background: 'none', border: 'none', cursor: 'pointer', opacity: 0.6 }}
                      title="Remove actor"
                    >✕</button>
                  )}
                </div>

                <div className="config-grid">
                  <div className="field-group">
                    <label>🎭 Personality & Traits</label>
                    <textarea
                      value={ag.traits}
                      onChange={(e) => mutate(i, 'traits', e.target.value)}
                      placeholder="Traits..."
                      rows={2}
                    />
                  </div>
                  <div className="field-group">
                    <label>🕵 Hidden Agenda</label>
                    <textarea
                      value={ag.hidden_agenda}
                      onChange={(e) => mutate(i, 'hidden_agenda', e.target.value)}
                      placeholder="Agenda..."
                      rows={2}
                    />
                  </div>
                </div>

                <div className="emotion-grid">
                  <div className="e-slider">
                    <div className="e-label">Tension <span>{Math.round(ag.emotions.tension * 100)}%</span></div>
                    <input type="range" min="0" max="1" step="0.05" value={ag.emotions.tension} onChange={(e) => mutateEmotion(i, 'tension', e.target.value)} />
                  </div>
                  <div className="e-slider">
                    <div className="e-label">Affection <span>{Math.round(ag.emotions.affection * 100)}%</span></div>
                    <input type="range" min="0" max="1" step="0.05" value={ag.emotions.affection} onChange={(e) => mutateEmotion(i, 'affection', e.target.value)} />
                  </div>
                  <div className="e-slider">
                    <div className="e-label">Energy <span>{Math.round(ag.emotions.energy * 100)}%</span></div>
                    <input type="range" min="0" max="1" step="0.05" value={ag.emotions.energy} onChange={(e) => mutateEmotion(i, 'energy', e.target.value)} />
                  </div>
                  <div className="e-slider">
                    <div className="e-label">Suspicion <span>{Math.round(ag.emotions.suspicion * 100)}%</span></div>
                    <input type="range" min="0" max="1" step="0.05" value={ag.emotions.suspicion} onChange={(e) => mutateEmotion(i, 'suspicion', e.target.value)} />
                  </div>
                </div>

                <div className="config-grid" style={{ marginTop: '12px' }}>
                  <select value={ag.llm_config.provider} onChange={(e) => mutate(i, 'provider', e.target.value)}>
                    <option value="lm_studio">LM Studio</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="google">Google</option>
                  </select>
                  <input type="text" value={ag.llm_config.model_name} onChange={(e) => mutate(i, 'model_name', e.target.value)} placeholder="Model" />
                </div>
              </div>
            ))}
            <button className="btn-add" onClick={addAgent}>+ Add Character</button>
          </div>
        )}

        <div className="mfoot">
          <button 
            className="cb red" 
            style={{ marginRight: 'auto' }}
            onClick={() => {
              if (window.confirm("⚠️ This will WIPE ALL character overrides and revert to system defaults. Are you sure?")) {
                onSystemReset();
                onClose();
              }
            }}
          >
            Factory Reset
          </button>
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-pri" onClick={() => onSave(agents, { sceneName, location, lighting, props })}>Save &amp; Apply</button>
        </div>
      </div>
    </div>
  )
}
