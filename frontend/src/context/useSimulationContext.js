/**
 * Consumer hook for the simulation context.
 *
 * Split out from SimulationContext.jsx so that module exports only the provider
 * component, which keeps React Fast Refresh working.
 */
import { useContext } from 'react'
import { SimulationContext } from './simulation-context'

export function useSimulationContext() {
  const ctx = useContext(SimulationContext)
  if (!ctx) throw new Error('useSimulationContext must be used inside SimulationProvider')
  return ctx
}
