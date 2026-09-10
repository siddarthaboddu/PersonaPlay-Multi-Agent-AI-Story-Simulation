import { useSimulationContext } from '../../context/SimulationContext'

export function Topbar({ onOpenConfig }) {
  const { 
    isConnected,    startScene, 
    nextTurn, 
    retakeTurn,
    auto, 
    setAuto, 
    pause,
    isProcessing,
    autoCountdown,
    turnCount, 
    currentBeat,
    phasesEnabled,
    togglePhases 
  } = useSimulationContext()

  return (
    <div className="topbar">
      <div className="tb-brand">
        <div className="tb-brand-icon">🎭</div>
        <span className="tb-brand-title">PersonaPlay</span>
        <span className="tb-brand-badge">Pro</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '12px' }}>
        <button className="cb" onClick={startScene} disabled={isProcessing} title="Start scene from beginning">
          {turnCount === 0 ? "▶ Start" : "🔄 Reset"}
        </button>

        <button className="cb purple" onClick={nextTurn} disabled={isProcessing} title="Step to next turn">
          {isProcessing ? "⏳ Thinking…" : "⚡ Next Turn"}
        </button>

        <button 
          className="cb" 
          onClick={retakeTurn} 
          disabled={isProcessing || turnCount === 0} 
          title="Cut! Re-roll this actor's line..."
          style={{ 
            opacity: (isProcessing || turnCount === 0) ? 0.4 : 0.9, 
            borderColor: 'rgba(245,166,35,0.35)', 
            color: 'var(--amber)' 
          }}
        >
          🎲 Retake
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

        {auto && (
          <button
            className="cb"
            onClick={pause}
            title="Pause simulation to manually speak or direct"
            style={{
              background: 'rgba(245, 166, 35, 0.18)',
              borderColor: 'rgba(245, 166, 35, 0.4)',
              color: 'var(--amber)',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <span>⏸ Pause</span>
          </button>
        )}
      </div>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={() => togglePhases(!phasesEnabled)}
          title={phasesEnabled 
            ? "Dramatic Phases Active: Click to switch to Direct Casual Conversation (no scripted phases)" 
            : "Direct Conversation Active: Click to enable Dramatic 20-Phase Arc"}
          style={{ 
            fontSize: '11px', 
            color: phasesEnabled ? 'var(--amber)' : '#38bdf8', 
            background: phasesEnabled ? 'rgba(245,166,35,0.08)' : 'rgba(56,189,248,0.1)', 
            border: `1px solid ${phasesEnabled ? 'rgba(245,166,35,0.25)' : 'rgba(56,189,248,0.35)'}`, 
            padding: '3px 10px', 
            borderRadius: '12px', 
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          {phasesEnabled ? (
            <>
              <span style={{ opacity: 0.6, textTransform: 'uppercase', fontSize: '9px' }}>Phase</span>
              <span>{currentBeat ? currentBeat[2] : 'COLD OPEN'}</span>
              <span style={{ opacity: 0.45, fontSize: '9px', marginLeft: 2 }} title="Click to toggle Direct Convo">⇄ Direct</span>
            </>
          ) : (
            <>
              <span>💬 Direct Convo</span>
              <span style={{ opacity: 0.45, fontSize: '9px', marginLeft: 2 }} title="Click to toggle Dramatic Phases">⇄ Phases</span>
            </>
          )}
        </button>

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

