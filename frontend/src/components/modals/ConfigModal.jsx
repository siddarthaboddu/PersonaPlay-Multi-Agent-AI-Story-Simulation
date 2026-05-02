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

import { useState } from 'react'

export function ConfigModal({ isOpen, onClose, onSave, onTest, testResults }) {
  const [agents, setAgents] = useState([
    {
      id: 'Alex',
      hidden_agenda: "Wants to convince Jamie to skip college and drive to Mexico. Secretly terrified of growing up.",
      llm_config: { ...DEFAULT_CONFIG },
    },
    {
      id: 'Jamie',
      hidden_agenda: "Just realized the mysterious duffel bag in the back belongs to a dangerous cartel. Wants to get home immediately without panicking Alex.",
      llm_config: { ...DEFAULT_CONFIG },
    },
  ])

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

  const addAgent = () =>
    setAgents([...agents, {
      id: `Character_${agents.length + 1}`,
      hidden_agenda: '',
      llm_config: { ...DEFAULT_CONFIG },
    }])

  const removeAgent = (i) => setAgents(agents.filter((_, idx) => idx !== i))

  return (
    <div className="overlay">
      <div className="modal">
        <div className="mtitle">🎭 Actor Roster &amp; LLM Config</div>

        {agents.map((ag, i) => (
          <div key={i} className="ccard">
            <div className="chead">
              <div style={{
                width: 30, height: 30, borderRadius: '50%',
                background: agentColor(i),
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 800, color: '#fff',
                fontFamily: 'JetBrains Mono, monospace', flexShrink: 0,
              }}>
                {ag.id.substring(0, 2).toUpperCase()}
              </div>
              <input
                type="text" value={ag.id}
                onChange={(e) => mutate(i, 'id', e.target.value)}
                placeholder="Name" style={{ flex: 1, marginBottom: 0 }}
              />
              <button className="btn-test" onClick={() => onTest(ag.id, ag.llm_config)}>Test</button>
              <Badge id={ag.id} results={testResults} />
              {agents.length > 1 && (
                <button
                  onClick={() => removeAgent(i)}
                  style={{ marginLeft: 6, fontSize: 14, color: 'var(--red)', background: 'none', border: 'none', cursor: 'pointer' }}
                  title="Remove actor"
                >✕</button>
              )}
            </div>

            {testResults[ag.id]?.status === 'error' && (
              <div style={{ fontSize: 12, color: '#fc8181', padding: '6px 10px', background: 'rgba(252,129,129,.08)', borderRadius: 6, marginBottom: 8 }}>
                {testResults[ag.id].message}
              </div>
            )}

            <input
              type="text" value={ag.hidden_agenda}
              onChange={(e) => mutate(i, 'hidden_agenda', e.target.value)}
              placeholder="🕵 Hidden agenda (the AI uses this secretly)"
            />

            <div className="crow2">
              <select
                value={ag.llm_config.provider}
                onChange={(e) => mutate(i, 'provider', e.target.value)}
                style={{ flex: '0 0 155px' }}
              >
                <option value="lm_studio">LM Studio (Local)</option>
                <option value="openrouter">OpenRouter (Cloud)</option>
                <option value="google">Google GenAI</option>
              </select>
              <input
                type="text" value={ag.llm_config.model_name}
                onChange={(e) => mutate(i, 'model_name', e.target.value)}
                placeholder="Model name"
              />
            </div>

            <input
              type="password" value={ag.llm_config.api_key}
              onChange={(e) => mutate(i, 'api_key', e.target.value)}
              placeholder="API Key (leave blank for LM Studio)"
            />
          </div>
        ))}

        <button className="btn-add" onClick={addAgent}>+ Add Character</button>

        <div className="mfoot">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-pri" onClick={() => onSave(agents)}>Save &amp; Apply</button>
        </div>
      </div>
    </div>
  )
}
