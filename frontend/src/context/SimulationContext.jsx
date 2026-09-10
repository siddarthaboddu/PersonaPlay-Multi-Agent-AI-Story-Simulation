/**
 * SimulationContext — provides simulation state and actions to the component tree.
 * Avoids prop drilling across the 3-panel layout.
 */
import { createContext, useContext } from 'react'
import { useSimulation } from '../hooks/useSimulation'
import { useWebSocket } from '../hooks/useWebSocket'

export const SimulationContext = createContext(null)

export function SimulationProvider({ children }) {
  const { isConnected, send, subscribe } = useWebSocket()
  const simulation = useSimulation(send, subscribe)

  return (
    <SimulationContext.Provider value={{ ...simulation, isConnected, send }}>
      {children}
    </SimulationContext.Provider>
  )
}

export function useSimulationContext() {
  const ctx = useContext(SimulationContext)
  if (!ctx) throw new Error('useSimulationContext must be used inside SimulationProvider')
  return ctx
}
