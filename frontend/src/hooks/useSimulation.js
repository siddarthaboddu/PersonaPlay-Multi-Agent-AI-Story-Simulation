/**
 * useSimulation — owns all simulation state and action dispatchers.
 *
 * Consumes the WS subscription API to register typed message handlers.
 * Exposes state and action functions to the rest of the UI via context.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { BEATS, getBeat, getBeatProgress } from '../constants/beats'

const AUTO_TURN_DELAY = parseInt(import.meta.env.VITE_AUTO_TURN_DELAY ?? '3200', 10)

export function useSimulation(send, subscribe) {
  const [messages,   setMessages]   = useState([{ type: 'action', content: '[SYSTEM]: Ready — press ▶ Start Scene to begin.' }])
  const [monologues, setMonologues] = useState([])
  const [vitals,     setVitals]     = useState({ tension: 0.5, turn_count: 0 })
  const [world,      setWorld]      = useState({ location: 'Unknown', lighting: 'Unknown', props: [] })
  const [agents,     setAgents]     = useState([])
  const [beats,      setBeats]      = useState(BEATS)   // hydrated from /api/beats on mount

  const autoRef  = useRef(false)
  const timerRef = useRef(null)
  const [auto, _setAuto] = useState(false)

  const setAuto = useCallback((val) => {
    autoRef.current = val
    _setAuto(val)
  }, [])

  // ── Fetch authoritative beats from backend (single source of truth) ────────
  useEffect(() => {
    fetch(
      (import.meta.env.VITE_API_URL ?? 'http://localhost:8000') + '/api/beats'
    )
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          // Convert to the [start, end, label] tuple format
          setBeats(data.map((b) => [b.start, b.end, b.label]))
        }
      })
      .catch(() => { /* fallback to local BEATS constant — non-fatal */ })
  }, [])

  // ── Browser download helper ────────────────────────────────────────────────
  const triggerDownload = useCallback((filename, content) => {
    const blob = new Blob([content], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
  }, [])

  // ── Subscribe to WS message types ─────────────────────────────────────────
  useEffect(() => {
    const unsubs = [
      subscribe('dialogue', (d) => {
        setMessages((p) => [...p, d])
      }),
      subscribe('action', (d) => {
        setMessages((p) => [...p, d])
      }),
      subscribe('monologue', (d) => {
        setMonologues((p) => [...p, d])
      }),
      subscribe('world_update',  (d) => setWorld(d.world)),
      subscribe('agents_update', (d) => setAgents(d.agents)),
      subscribe('image_update',  (d) => setMessages((p) => [...p, { type: 'image', url: d.url, prompt: d.prompt }])),
      subscribe('history_reset', (d) => {
        setMessages(d.messages ?? [])
        setMonologues(d.monologues ?? [])
      }),
      subscribe('vitals_update', (d) => {
        setVitals(d.vitals)
        if (autoRef.current) {
          clearTimeout(timerRef.current)
          timerRef.current = setTimeout(() => {
            if (autoRef.current) send({ type: 'next_turn' })
          }, AUTO_TURN_DELAY)
        }
      }),
      subscribe('download', (d) => triggerDownload(d.filename, d.content)),
      subscribe('error', (d) => {
        console.error('[WS Error]', d.code, d.detail)
        setMessages((p) => [...p, {
          type: 'action',
          content: `[ERROR]: ${d.detail}`,
        }])
      }),
    ]
    return () => unsubs.forEach((u) => u())
  }, [subscribe, send, triggerDownload])

  // ── Action dispatchers ─────────────────────────────────────────────────────
  const startScene    = useCallback(() => send({ type: 'start_scene' }), [send])
  const stopScene     = useCallback(() => { setAuto(false); send({ type: 'stop_scene' }) }, [send, setAuto])
  const nextTurn      = useCallback(() => send({ type: 'next_turn' }), [send])
  const rewind        = useCallback((turns = 3) => send({ type: 'rewind_turns', turns }), [send])
  const exportScript  = useCallback(() => send({ type: 'export_script' }), [send])
  const changeScene   = useCallback((location) => send({ type: 'change_scene', location }), [send])
  const injectChaos   = useCallback((command) => send({ type: 'director_command', command }), [send])
  const generateImage = useCallback(() => send({ type: 'director_command', command: 'generate image' }), [send])
  const forceTension  = useCallback((value) => send({ type: 'force_scene_tension', value }), [send])
  const forceEmotion  = useCallback((agent_id, emotion, value) => send({ type: 'force_emotion', agent_id, emotion, value }), [send])
  const forceGiveProp = useCallback((prop_id, owner) => send({ type: 'force_give_prop', prop_id, owner }), [send])
  const configureScene = useCallback((agents) => send({ type: 'configure_scene', agents }), [send])
  const checkModel    = useCallback((agent_id, llm_config) => send({ type: 'check_model', agent_id, llm_config }), [send])
  const pause         = useCallback(() => {
    setAuto(false)
    setMessages((p) => [...p, { type: 'action', content: '[SYSTEM]: ⏸ Paused.' }])
  }, [setAuto])

  // ── Derived beat state ─────────────────────────────────────────────────────
  const turnCount    = vitals.turn_count ?? 0
  const currentBeat  = getBeat(turnCount)
  const beatProgress = getBeatProgress(turnCount)

  return {
    // State
    messages, monologues, vitals, world, agents, beats,
    auto, setAuto,
    turnCount, currentBeat, beatProgress,
    // Actions
    startScene, stopScene, nextTurn, rewind, exportScript,
    changeScene, injectChaos, generateImage,
    forceTension, forceEmotion, forceGiveProp,
    configureScene, checkModel, pause,
  }
}
