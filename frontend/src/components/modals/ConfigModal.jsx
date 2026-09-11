import { agentColor } from '../../utils/colors'
import { Badge } from '../shared/Badge'
import { STARTING_BLUEPRINTS } from '../../constants/blueprints'

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

const parseRelationshipContext = (text = '') => Object.fromEntries(
  text
    .split('\n')
    .map(line => line.split(/:(.*)/, 2))
    .filter(([name, note]) => name.trim() && note?.trim())
    .map(([name, note]) => [name.trim(), note.trim()])
)

const SAMPLE_YAML = `# PersonaPlay Blueprint: Casual Date Night
scene:
  name: "Sunday Living Room: The Takeout Debate"
  location: "Sunlit Apartment Living Room & Kitchenette"
  lighting: "Warm golden afternoon sun slicing through half-closed blinds"
agents:
  - id: "Maya"
    traits: "Playful, witty graphic designer with an expressive smirk and dry humor. Speaks casually with affectionate teasing."
    hidden_agenda: "Convince Liam to stay in and cook cheap pantry mac-and-cheese without spoiling the surprise concert passes at 7:00 PM."
    emotions: { tension: 0.35, affection: 0.9, energy: 0.6, suspicion: 0.2 }
  - id: "Liam"
    traits: "Warm, easygoing UX designer, prone to gentle overthinking and teasing banter. Loves spicy comfort food."
    hidden_agenda: "Persuade Maya that spicy Thai drunken noodles are the superior dinner choice today while reclaiming couch blanket."
    emotions: { tension: 0.25, affection: 0.9, energy: 0.55, suspicion: 0.2 }
props:
  - id: "takeout_menus"
    owner: "Liam"
    description: "A messy stack of takeout flyers: spicy Thai noodles, greasy pepperoni pizza, and burritos."
    visibility: "visible"
  - id: "surprise_concert_tickets"
    owner: "Maya"
    description: "Two VIP passes to Liam's favorite indie band tucked secretly inside her laptop sleeve."
    visibility: "hidden"
  - id: "fleece_blanket"
    owner: "Maya"
    description: "An oversized fluffy beige blanket that Maya has hogged nearly 90% of on the sofa."
    visibility: "visible"`


import { useState, useEffect } from 'react'
import yaml from 'js-yaml'

export function ConfigModal({ isOpen, onClose, onSave, onTest, testResults, currentScene, currentAgents, onSystemReset, onExportScript }) {
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
        setAgents(data.agents.map(a => {
          const prov = a.llm_config?.provider || 'lm_studio'
          const defBase = prov === 'openrouter' ? 'https://openrouter.ai/api/v1' : 'http://localhost:1234/v1'
          return {
            id: a.id || 'Unnamed',
            traits: a.traits || '',
            hidden_agenda: a.hidden_agenda || '',
            emotions: {
              tension: a.emotions?.tension ?? 0.5,
              affection: a.emotions?.affection ?? 0.5,
              energy: a.emotions?.energy ?? 0.5,
              suspicion: a.emotions?.suspicion ?? 0.5
            },
            relationships: a.relationships || {},
            relationship_context: a.relationship_context || {},
            llm_config: {
              provider: prov,
              model_name: a.llm_config?.model_name || 'local-model',
              api_key: a.llm_config?.api_key || '',
              base_url: a.llm_config?.base_url || defBase
            }
          }
        }))
      }
      if (data.props && Array.isArray(data.props)) {
        setProps(data.props.map(p => ({
          id: p.id || 'Prop',
          owner: p.owner || 'world',
          description: p.description || '',
          visibility: p.visibility || 'visible'
        })))
      } else {
        setProps([])
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
        relationships: a.relationships,
        relationship_context: a.relationship_context,
        llm_config: a.llm_config
      }))
    }
    setYamlText(yaml.dump(data, { indent: 2 }))
    setView('yaml')
  }

  const handleSelectBlueprint = (blueprintId) => {
    const bp = STARTING_BLUEPRINTS.find(b => b.id === blueprintId)
    if (!bp) return

    setSceneName(bp.scene.name)
    setLocation(bp.scene.location)
    setLighting(bp.scene.lighting)

    setProps(bp.props.map(p => ({
      id: p.id,
      owner: p.owner || 'world',
      description: p.description || '',
      visibility: p.visibility || 'visible',
    })))

    setAgents(bp.agents.map((a, idx) => {
      const existingLlm = agents[idx]?.llm_config || DEFAULT_CONFIG
      return {
        id: a.id,
        traits: a.traits,
        hidden_agenda: a.hidden_agenda,
        emotions: { ...a.emotions },
        relationships: a.relationships ? { ...a.relationships } : {},
        relationship_context: a.relationship_context ? { ...a.relationship_context } : {},
        llm_config: {
          provider: existingLlm.provider || a.llm_config?.provider || 'lm_studio',
          model_name: existingLlm.model_name || a.llm_config?.model_name || 'local-model',
          api_key: existingLlm.api_key || a.llm_config?.api_key || '',
          base_url: existingLlm.base_url || a.llm_config?.base_url || 'http://localhost:1234/v1',
        },
      }
    }))

    const dumpData = {
      scene: { ...bp.scene },
      props: bp.props,
      agents: bp.agents.map((a, idx) => {
        const existingLlm = agents[idx]?.llm_config || DEFAULT_CONFIG
        return {
          id: a.id,
          traits: a.traits,
          hidden_agenda: a.hidden_agenda,
          emotions: a.emotions,
          relationships: a.relationships,
          relationship_context: a.relationship_context,
          llm_config: {
            provider: existingLlm.provider || a.llm_config?.provider || 'lm_studio',
            model_name: existingLlm.model_name || a.llm_config?.model_name || 'local-model',
            api_key: existingLlm.api_key || a.llm_config?.api_key || '',
            base_url: existingLlm.base_url || a.llm_config?.base_url || 'http://localhost:1234/v1',
          },
        }
      }),
    }
    setYamlText(yaml.dump(dumpData, { indent: 2 }))
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
            id: 'Maya',
            traits: 'Playful, witty graphic designer with an expressive smirk and dry humor. Speaks casually with affectionate teasing, lounging comfortably under a pile of cushions.',
            hidden_agenda: 'You blew the weekend dinner budget on surprise concert passes for Liam tonight. You must convince Liam to stay in and cook cheap pantry mac-and-cheese without spoiling the concert reveal at 7:00 PM.',
            emotions: { tension: 0.35, affection: 0.9, energy: 0.6, suspicion: 0.2 },
            relationships: {
              'Liam': { trust: 0.9, affinity: 0.92, fear: 0.05, dominance: 0.55 },
            },
            llm_config: { ...DEFAULT_CONFIG },
          },
          {
            id: 'Liam',
            traits: 'Warm, easygoing UX designer, prone to gentle overthinking and teasing banter. Loves cozy weekend routines, spicy comfort food, and stealing back blanket corners.',
            hidden_agenda: 'You promised Maya she could pick dinner, but you have had an intense craving for extra-spicy Thai drunken noodles all day. Persuade Maya that Thai food is the superior choice today while reclaiming some blanket.',
            emotions: { tension: 0.25, affection: 0.9, energy: 0.55, suspicion: 0.2 },
            relationships: {
              'Maya': { trust: 0.9, affinity: 0.92, fear: 0.05, dominance: 0.45 },
            },
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
      relationship_context: {},
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

        {/* Quick Scenario Blueprint Presets */}
        <div style={{
          padding: '12px 16px',
          marginBottom: '16px',
          borderRadius: 'var(--r-sm)',
          background: 'linear-gradient(135deg, rgba(245, 208, 97, 0.1) 0%, rgba(167, 139, 250, 0.08) 100%)',
          border: '1px solid rgba(245, 208, 97, 0.3)',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--gold)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              ⚡ Scenario Presets
            </span>
            <span style={{ fontSize: '11px', color: 'var(--t3)', fontStyle: 'italic' }}>
              Click any starter to load complete world, props &amp; characters
            </span>
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {STARTING_BLUEPRINTS.map(bp => (
              <button
                key={bp.id}
                type="button"
                onClick={() => handleSelectBlueprint(bp.id)}
                title={bp.tagline}
                style={{
                  background: 'rgba(5, 7, 15, 0.65)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-pill)',
                  padding: '5px 11px',
                  fontSize: '11.5px',
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--t2)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  transition: 'all 0.15s ease',
                }}
              >
                <span>{bp.title.split(' ')[0]}</span>
                <span style={{ fontWeight: 700 }}>{bp.title.split(' ').slice(1, 3).join(' ')}</span>
                <span style={{ opacity: 0.5, fontSize: '9.5px', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>({bp.genre.split(' ')[0]})</span>
              </button>
            ))}
          </div>
        </div>

        {view === 'yaml' ? (
          <div className="yaml-box">
            <div className="yaml-hint">
              Paste a YAML blueprint below or click any preset above to populate.
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
            <div className="ccard" style={{ borderLeftColor: 'var(--gold)', padding: '16px' }}>
              <div className="chead" style={{ fontWeight: 800, fontSize: 13, textTransform: 'uppercase', color: 'var(--gold)', marginBottom: '12px' }}>
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

            {/* Props Section (Collapsible) */}
            <details className="ccard" style={{ borderLeftColor: 'var(--cyan)', padding: '14px 16px', marginTop: '16px' }}>
              <summary style={{ fontWeight: 800, fontSize: 13, textTransform: 'uppercase', color: 'var(--cyan)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', userSelect: 'none' }}>
                <span>📦 Scene Props ({props.length})</span>
                <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--t3)', textTransform: 'none' }}>click to expand / edit</span>
              </summary>
              
              <div style={{ marginTop: '14px' }}>
                {props.map((p, i) => (
                  <div key={i} className="prop-row" style={{ marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1.2fr 1fr auto', gap: '8px', marginBottom: '6px' }}>
                      <input
                        type="text" value={p.id}
                        onChange={(e) => mutateProp(i, 'id', e.target.value)}
                        placeholder="Prop ID"
                        style={{ fontWeight: 700, fontSize: '12px' }}
                      />
                      <select value={p.owner} onChange={(e) => mutateProp(i, 'owner', e.target.value)} style={{ fontSize: '12px' }}>
                        <option value="world">In World</option>
                        {agents.map(ag => (
                          <option key={ag.id} value={ag.id}>Owned by {ag.id}</option>
                        ))}
                      </select>
                      <select value={p.visibility} onChange={(e) => mutateProp(i, 'visibility', e.target.value)} style={{ fontSize: '12px' }}>
                        <option value="visible">Visible</option>
                        <option value="hidden">Hidden</option>
                      </select>
                      <button onClick={() => removeProp(i)} title="Remove Prop" style={{ color: 'var(--red)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '14px', padding: '0 4px' }}>✕</button>
                    </div>
                    <input
                      type="text"
                      className="prop-desc"
                      value={p.description}
                      onChange={(e) => mutateProp(i, 'description', e.target.value)}
                      placeholder="Brief prop description..."
                      style={{ fontSize: '12px', padding: '5px 8px' }}
                    />
                  </div>
                ))}
                <button className="btn-add" style={{ padding: '6px 14px', fontSize: '11px', marginTop: '4px' }} onClick={addProp}>+ Add Prop</button>
              </div>
            </details>

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
                  <div className="field-group">
                    <label>🤝 Relationship Context</label>
                    <textarea
                      value={ag.relationship_context_text ?? Object.entries(ag.relationship_context || {}).map(([name, note]) => `${name}: ${note}`).join('\n')}
                      onChange={(e) => mutate(i, 'relationship_context_text', e.target.value)}
                      placeholder="Liam: Your longtime friend; teasing is normal, but honesty matters."
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
                <div className="config-grid" style={{ marginTop: '8px' }}>
                  <input 
                    type="text" 
                    value={ag.llm_config.base_url || ''} 
                    onChange={(e) => mutate(i, 'base_url', e.target.value)} 
                    placeholder={ag.llm_config.provider === 'openrouter' ? 'https://openrouter.ai/api/v1' : 'http://localhost:1234/v1'} 
                  />
                  <input 
                    type="password" 
                    value={ag.llm_config.api_key || ''} 
                    onChange={(e) => mutate(i, 'api_key', e.target.value)} 
                    placeholder="API Key (optional if in .env)" 
                  />
                </div>
              </div>
            ))}
            <button className="btn-add" onClick={addAgent}>+ Add Character</button>
          </div>
        )}

        <div className="mfoot">
          <div style={{ display: 'flex', gap: 8, marginRight: 'auto' }}>
            <button 
              className="cb red" 
              onClick={() => {
                if (window.confirm("⚠️ This will WIPE ALL character overrides and revert to system defaults. Are you sure?")) {
                  onSystemReset();
                  onClose();
                }
              }}
            >
              Factory Reset
            </button>
            {onExportScript && (
              <button 
                type="button"
                className="cb amber"
                onClick={onExportScript}
                title="Export complete session script as text"
              >
                ⬇ Export Script
              </button>
            )}
          </div>

          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-pri" onClick={() => onSave(
            agents.map(agent => ({
              ...agent,
              relationship_context: parseRelationshipContext(
                agent.relationship_context_text ?? Object.entries(agent.relationship_context || {}).map(([name, note]) => `${name}: ${note}`).join('\n')
              ),
            })),
            { sceneName, location, lighting, props }
          )}>Save &amp; Apply</button>
        </div>
      </div>
    </div>
  )
}
