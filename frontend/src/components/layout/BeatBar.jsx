import { useSimulationContext } from '../../context/SimulationContext'

export function BeatBar() {
  const { turnCount, currentBeat, beatProgress } = useSimulationContext()

  return (
    <div className="beatbar">
      <span className="beat-label">Narrative</span>
      <span className="beat-name">{currentBeat[2]}</span>
      <div className="beat-track">
        <div className="beat-fill" style={{ width: `${beatProgress * 100}%` }} />
      </div>
      <span className="beat-desc">Turn {turnCount} of {currentBeat[1]}</span>
    </div>
  )
}
