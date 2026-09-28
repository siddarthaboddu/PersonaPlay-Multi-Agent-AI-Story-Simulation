/**
 * The React context object itself.
 *
 * Kept in its own module (rather than alongside the provider component) so that
 * `react-refresh/only-export-components` is satisfied: a module that exports
 * both a component and a plain constant cannot be hot-reloaded safely.
 */
import { createContext } from 'react'

export const SimulationContext = createContext(null)
