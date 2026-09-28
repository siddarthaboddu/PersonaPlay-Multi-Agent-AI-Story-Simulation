import { useState } from 'react'
import { useSimulationContext } from './context/useSimulationContext'
import { Topbar } from './components/layout/Topbar'
import { DirectorPanel } from './components/panels/DirectorPanel'
import { TheaterPanel } from './components/panels/TheaterPanel'
import { BackstagePanel } from './components/panels/BackstagePanel'
import { ConfigModal } from './components/modals/ConfigModal'

export default function App() {
  const { 
    configureScene, checkModel, vitals, world, agents, systemReset, exportScript
  } = useSimulationContext()
  
  const [cfgOpen, setCfgOpen] = useState(false)
  const [testRes, setTestRes] = useState({})

  return (
    <div className="shell">
      {/* `key` forces a remount each time the modal opens, so ConfigModal's
          lazy useState initializers re-seed from the current scene/agents. */}
      <ConfigModal
        key={cfgOpen ? 'open' : 'closed'}
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
        onExportScript={exportScript}
      />

      <Topbar onOpenConfig={() => setCfgOpen(true)} />


      <div className="dash">
        <DirectorPanel />
        <TheaterPanel />
        <BackstagePanel />
      </div>
    </div>
  )
}
