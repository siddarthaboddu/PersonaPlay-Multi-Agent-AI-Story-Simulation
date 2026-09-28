/**
 * SimulationContext — provides simulation state and actions to the component tree.
 * Avoids prop drilling across the 3-panel layout.
 *
 * This module intentionally exports ONLY the provider component. The context
 * object and the consumer hook live in sibling modules so that
 * `react-refresh/only-export-components` stays satisfied and the provider can
 * still be hot-reloaded during development.
 */
import { SimulationContext } from './simulation-context'
import { useSimulation } from '../hooks/useSimulation'
import { useWebSocket } from '../hooks/useWebSocket'

export function SimulationProvider({ children }) {
  const { isConnected, send, subscribe } = useWebSocket()
  const simulation = useSimulation(send, subscribe)

  return (
    <SimulationContext.Provider value={{ ...simulation, isConnected, send }}>
      {children}
    </SimulationContext.Provider>
  )
}
