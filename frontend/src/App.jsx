import { useState } from 'react'
import { useSimulationContext } from './context/SimulationContext'
import { Topbar } from './components/layout/Topbar'
import { BeatBar } from './components/layout/BeatBar'
import { DirectorPanel } from './components/panels/DirectorPanel'
import { TheaterPanel } from './components/panels/TheaterPanel'
import { BackstagePanel } from './components/panels/BackstagePanel'
import { ConfigModal } from './components/modals/ConfigModal'

export default function App() {
  const { 
    configureScene, checkModel, vitals, world, agents, systemReset, startScene
  } = useSimulationContext()
  
  const [cfgOpen, setCfgOpen] = useState(false)
  const [testRes, setTestRes] = useState({})

  return (
    <div className="shell">
      <ConfigModal 
        isOpen={cfgOpen} 
        onClose={() => setCfgOpen(false)}
        currentScene={{ active_scene: vitals.scene_name, world_state: world }}
        currentAgents={agents}
        onSave={(agents, metadata) => {
          configureScene(agents, metadata)
          setCfgOpen(false)
        }}
        onTest={(id, cfg) => {
          setTestRes(prev => ({ ...prev, [id]: { status: 'loading' } }))
          checkModel(id, cfg)
        }}
        testResults={testRes}
        onSystemReset={systemReset}
      />

      <Topbar onOpenConfig={() => setCfgOpen(true)} />
      <BeatBar />

      <div className="dash">
        <DirectorPanel />
        <TheaterPanel />
        <BackstagePanel />
      </div>
    </div>
  )
}
