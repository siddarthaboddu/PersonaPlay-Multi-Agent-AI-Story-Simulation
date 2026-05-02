import { useSimulationContext } from '../../context/SimulationContext'

export function Topbar({ onOpenConfig }) {
  const { 
    isConnected, startScene, stopScene, pause, 
    nextTurn, rewind, exportScript, turnCount 
  } = useSimulationContext()

  return (
    <div className="topbar">
      <div className="logo">
        <div className="logo-gem">🎭</div>
        <div className="logo-text">
          <div className="name">Persona<em>Play</em> Pro</div>
          <div className="sub">Multi-Agent Theater Engine</div>
        </div>
      </div>
      <div className="tsep"/>

      <div className="ctrl-group">
        <button className="cb green" onClick={startScene}>▶ Start Scene</button>
        <button className="cb"       onClick={pause}>⏸ Pause</button>
        <button className="cb red"   onClick={stopScene}>⏹ Stop</button>
      </div>
      <div className="tsep"/>
      <div className="ctrl-group">
        <button className="cb purple" onClick={nextTurn}>⚡ Next Turn</button>
        <button className="cb cyan"   onClick={() => rewind(3)}>⏪ Rewind</button>
        <button className="cb amber"  onClick={exportScript}>⬇ Export</button>
      </div>

      <div className="tb-right">
        <div className="turn-badge">Turn {turnCount}</div>
        <div className="ws-badge">
          <div className={`wdot ${isConnected ? 'on' : 'off'}`}/>
          {isConnected ? 'Connected' : 'Offline'}
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
