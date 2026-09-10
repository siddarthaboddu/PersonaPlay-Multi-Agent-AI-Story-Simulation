import { useState } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'
import { Toggle } from '../shared/Toggle'

export function DirectorPanel() {
  const { 
    auto, setAuto, tts, setTts, world, vitals, 
    agents, forceTension, forceGiveProp, changeScene, injectChaos 
  } = useSimulationContext()

  const [loc, setLoc] = useState('')
  const [cmd, setCmd] = useState('')
  const [whisperTarget, setWhisperTarget] = useState('')
  const [whisperText, setWhisperText] = useState('')

  const activeTarget = whisperTarget || (agents[0]?.id ?? '')

  return (
    <div className="panel">
      <div className="ph">
        <div className="ph-icon" style={{ background: 'rgba(167,139,250,.18)' }}>🎬</div>
        <span className="ph-title">Director</span>
      </div>
      <div className="pb">
        <Toggle label="Auto-Play" checked={auto} onChange={setAuto} icon="🎞" />
        <Toggle label="Voice (TTS)" checked={tts} onChange={setTts} icon="🔊" />

        <div className="rule"/>
        <div className="sec">🌍 World State</div>
        <div className="wcard">
          <div className="wrow"><span className="wl">📍 Location</span><span className="wv">{world.location}</span></div>
          <div className="wrow"><span className="wl">💡 Lighting</span><span className="wv">{world.lighting}</span></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="wl">🔥 Scene Tension</span>
              <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--amber)' }}>{Math.round((vitals.tension || 0.5) * 100)}%</span>
            </div>
            <div className="tension-track">
              <div className="tension-fill" style={{ width: `${(vitals.tension || 0.5) * 100}%` }}/>
            </div>
            <input 
              type="range" min="0" max="1" step="0.05" value={vitals.tension || 0.5}
              onChange={(e) => forceTension(parseFloat(e.target.value))}
              style={{ accentColor: 'var(--amber)', '--c': 'var(--amber)' }}
            />
          </div>
        </div>

        {world.props?.length > 0 && (
          <>
            <div className="sec">🎒 Props</div>
            {world.props.map(p => (
              <div key={p.id} className="prop-row">
                <span className="pname">{p.id.replace(/_/g, ' ')}</span>
                <select 
                  className="psel" 
                  value={p.owner === 'Nobody' ? 'world' : p.owner} 
                  onChange={(e) => forceGiveProp(p.id, e.target.value)}
                >
                  <option value="world">In World (Nobody)</option>
                  {agents.map(a => <option key={a.id} value={a.id}>{a.id}</option>)}
                </select>
              </div>
            ))}
          </>
        )}

        <div className="rule"/>
        <div className="sec">🚀 Teleport Scene</div>
        <form 
          style={{ display: 'flex', gap: 6 }} 
          onSubmit={(e) => {
            e.preventDefault();
            if (loc.trim()) {
              changeScene(loc);
              setLoc('');
            }
          }}
        >
          <input 
            type="text" placeholder="New location…" 
            value={loc} onChange={(e) => setLoc(e.target.value)} 
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn-go">Go</button>
        </form>

        <div className="sec">⚡ Inject Chaos</div>
        <form 
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }} 
          onSubmit={(e) => {
            e.preventDefault();
            if (cmd.trim()) {
              injectChaos(cmd);
              setCmd('');
            }
          }}
        >
          <input 
            type="text" placeholder="E.g. 'Police appear in the rear view'" 
            value={cmd} onChange={(e) => setCmd(e.target.value)}
          />
          <button type="submit" className="btn-chaos">🔥 Inject into Scene</button>
        </form>

        <div className="rule"/>
        <div className="sec">🤫 Secret Whisper (In-Ear Coaching)</div>
        <form 
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }} 
          onSubmit={(e) => {
            e.preventDefault();
            if (whisperText.trim() && activeTarget) {
              whisperDirective(activeTarget, whisperText.trim());
              setWhisperText('');
            }
          }}
        >
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--t3)', whiteSpace: 'nowrap' }}>To Actor:</span>
            <select
              className="psel"
              value={activeTarget}
              onChange={(e) => setWhisperTarget(e.target.value)}
              style={{ flex: 1 }}
            >
              {agents.map(a => <option key={a.id} value={a.id}>{a.id}</option>)}
            </select>
          </div>

          <input 
            type="text" 
            placeholder={`Secret directive for ${activeTarget || 'actor'}…`}
            value={whisperText} 
            onChange={(e) => setWhisperText(e.target.value)}
          />

          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {[
              "Play along, then double-cross",
              "Ask about their hidden past",
              "Demand proof immediately",
              "Conceal your fear with humor"
            ].map(preset => (
              <button
                key={preset}
                type="button"
                onClick={() => setWhisperText(preset)}
                style={{
                  fontSize: 10,
                  padding: '2px 6px',
                  borderRadius: 4,
                  border: '1px solid var(--border)',
                  background: 'var(--s2)',
                  color: 'var(--t3)',
                  cursor: 'pointer'
                }}
              >
                {preset}
              </button>
            ))}
          </div>

          <button 
            type="submit" 
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '7px 12px', borderRadius: 8, border: 'none',
              background: 'linear-gradient(135deg, var(--purple), #7c3aed)',
              color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer'
            }}
          >
            🤫 Whisper to {activeTarget || 'Actor'}
          </button>
        </form>
      </div>
    </div>
  )
}
