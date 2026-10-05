import { useSimulationContext } from '../../context/useSimulationContext'

export function Topbar({ onOpenConfig }) {
  const { 
    isConnected,    startScene, 
    nextTurn, 
    retakeTurn,
    stopScene,
    auto, 
    setAuto, 
    isProcessing,
    autoCountdown,
    turnCount,
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

        {/* Hard stop: cancels the in-flight turn and halts all automation. */}
        {(isProcessing || auto) && (
          <button
            className="cb"
            onClick={stopScene}
            title="Forcibly stop the running turn and halt auto-play"
            style={{
              background: 'rgba(248, 113, 113, 0.15)',
              borderColor: 'rgba(248, 113, 113, 0.4)',
              color: 'var(--red)',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <span>🛑 Stop</span>
          </button>
        )}
      </div>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
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

