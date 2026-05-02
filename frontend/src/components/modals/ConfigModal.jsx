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

import { useState, useEffect } from 'react'

export function ConfigModal({ isOpen, onClose, onSave, onTest, testResults, currentScene, currentAgents }) {
  const [sceneName, setSceneName] = useState('')
  const [location, setLocation] = useState('')
  const [lighting, setLighting] = useState('')
  const [agents, setAgents] = useState([])

  // Sync state with props whenever modal opens
  useEffect(() => {
    if (isOpen) {
      setSceneName(currentScene?.active_scene || '')
      setLocation(currentScene?.world_state?.location || '')
      setLighting(currentScene?.world_state?.lighting || '')
      
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
        <div className="mtitle">🎭 Simulation Blueprint</div>

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

            {testResults[ag.id]?.status === 'error' && (
              <div style={{ fontSize: 12, color: '#fc8181', padding: '10px 14px', background: 'rgba(252,129,129,.08)', border: '1px solid rgba(252,129,129,.2)', borderRadius: 10, marginBottom: 16 }}>
                <strong>Configuration Error:</strong> {testResults[ag.id].message}
              </div>
            )}

            <div className="config-grid">
              <div className="field-group">
                <label>🎭 Personality & Traits</label>
                <div className="hint">Influences vocabulary and speaking style</div>
                <textarea
                  value={ag.traits}
                  onChange={(e) => mutate(i, 'traits', e.target.value)}
                  placeholder="e.g. Sarcastic, technological genius, speaks in short sentences."
                  rows={2}
                />
              </div>

              <div className="field-group">
                <label>🕵 Hidden Agenda</label>
                <div className="hint">The secret goal the AI pursues through subtext</div>
                <textarea
                  value={ag.hidden_agenda}
                  onChange={(e) => mutate(i, 'hidden_agenda', e.target.value)}
                  placeholder="What does this character secretly want to achieve?"
                  rows={3}
                />
              </div>
            </div>

            <div className="field-group" style={{ marginTop: '12px' }}>
              <label>💓 Starting Emotional State</label>
              <div className="hint">Set the initial psychological baseline for the scene</div>
              <div className="emotion-grid">
                <div className="e-slider">
                  <div className="e-label">Tension <span>{Math.round(ag.emotions.tension * 100)}%</span></div>
                  <input 
                    type="range" min="0" max="1" step="0.05" 
                    style={{ '--c': 'var(--red)' }}
                    value={ag.emotions.tension} 
                    onChange={(e) => mutateEmotion(i, 'tension', e.target.value)} 
                  />
                </div>
                <div className="e-slider">
                  <div className="e-label">Affection <span>{Math.round(ag.emotions.affection * 100)}%</span></div>
                  <input 
                    type="range" min="0" max="1" step="0.05" 
                    style={{ '--c': 'var(--pink)' }}
                    value={ag.emotions.affection} 
                    onChange={(e) => mutateEmotion(i, 'affection', e.target.value)} 
                  />
                </div>
                <div className="e-slider">
                  <div className="e-label">Energy <span>{Math.round(ag.emotions.energy * 100)}%</span></div>
                  <input 
                    type="range" min="0" max="1" step="0.05" 
                    style={{ '--c': 'var(--green)' }}
                    value={ag.emotions.energy} 
                    onChange={(e) => mutateEmotion(i, 'energy', e.target.value)} 
                  />
                </div>
                <div className="e-slider">
                  <div className="e-label">Suspicion <span>{Math.round(ag.emotions.suspicion * 100)}%</span></div>
                  <input 
                    type="range" min="0" max="1" step="0.05" 
                    style={{ '--c': 'var(--cyan)' }}
                    value={ag.emotions.suspicion} 
                    onChange={(e) => mutateEmotion(i, 'suspicion', e.target.value)} 
                  />
                </div>
              </div>
            </div>

            <div className="field-group" style={{ marginTop: '12px' }}>
              <label>⚙️ LLM Configuration</label>
              <div className="crow2">
                <select
                  value={ag.llm_config.provider}
                  onChange={(e) => mutate(i, 'provider', e.target.value)}
                  style={{ flex: '0 0 160px' }}
                >
                  <option value="lm_studio">LM Studio (Local)</option>
                  <option value="openrouter">OpenRouter (Cloud)</option>
                  <option value="google">Google GenAI</option>
                </select>
                <input
                  type="text" value={ag.llm_config.model_name}
                  onChange={(e) => mutate(i, 'model_name', e.target.value)}
                  placeholder="Model Identifier"
                />
              </div>
              <input
                type="password" value={ag.llm_config.api_key}
                onChange={(e) => mutate(i, 'api_key', e.target.value)}
                placeholder="Provider API Key (if required)"
                style={{ marginTop: '8px' }}
              />
            </div>
          </div>
        ))}

        <button className="btn-add" onClick={addAgent}>+ Add Character</button>

        <div className="mfoot">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-pri" onClick={() => onSave(agents, { sceneName, location, lighting })}>Save &amp; Apply</button>
        </div>
      </div>
    </div>
  )
}
