import { useSimulationContext } from '../../context/SimulationContext'

export function Topbar({ onOpenConfig }) {
  const { 
    isConnected, startScene, 
    nextTurn, turnCount, currentBeat,
    auto, setAuto, autoCountdown, isProcessing
  } = useSimulationContext()

  return (
    <div className="topbar">
      <div className="logo">
        <div className="logo-gem">🎭</div>
        <div className="logo-text">
          <div className="name">Persona<em>Play</em> Pro</div>
          <div className="sub">Multi-Agent AI Story Simulation</div>
        </div>
      </div>
      <div className="tsep"/>

      {/* Main Transport Controls */}
      <div className="ctrl-group">
        <button className="cb green" onClick={startScene}>
          {turnCount > 0 ? "🔄 Reset Session" : "▶ Start Scene"}
        </button>

        <button className="cb purple" onClick={nextTurn} disabled={isProcessing} title="Step to next turn">
          {isProcessing ? "⏳ Thinking…" : "⚡ Next Turn"}
        </button>

        <button 
          className={`cb ${auto ? 'green' : ''}`}
          onClick={() => setAuto(!auto)}
          style={auto ? {
            background: 'rgba(34, 197, 94, 0.22)',
            borderColor: 'var(--green)',
            color: '#4ade80',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 0 10px rgba(74, 222, 128, 0.2)'
          } : {
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title={auto ? "Automated Mode is ON. Click to Pause." : "Turn ON Automated Mode."}
        >
          <span>{auto ? "🟢 Auto: ON" : "⚪ Auto: OFF"}</span>
          {auto && autoCountdown !== null && (
            <span style={{
              background: 'rgba(0,0,0,0.4)',
              borderRadius: '8px',
              padding: '1px 5px',
              fontSize: '10px',
              fontFamily: 'JetBrains Mono, monospace'
            }}>
              {autoCountdown}s
            </span>
          )}
        </button>
      </div>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
        {currentBeat && (
          <div style={{ 
            fontSize: '11px', 
            color: 'var(--amber)', 
            background: 'rgba(245,166,35,0.08)', 
            border: '1px solid rgba(245,166,35,0.2)', 
            padding: '3px 10px', 
            borderRadius: '12px', 
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ opacity: 0.6, textTransform: 'uppercase', fontSize: '9px' }}>Phase</span>
            <span>{currentBeat[2]}</span>
          </div>
        )}

        <div className="turn-badge">Turn {turnCount}</div>
        <div className="ws-badge">
          <div className={`wdot ${isConnected ? 'on' : 'off'}`}/>
          {isConnected ? 'Live' : 'Offline'}
        </div>
        <button 
          className="cb" 
          style={{ borderColor: 'rgba(167,139,250,.4)', color: 'var(--purple)', background: 'rgba(167,139,250,.1)' }}
          onClick={onOpenConfig}
        >
          ⚙ Configure
        </button>
      </div>
    </div>
  )
}

