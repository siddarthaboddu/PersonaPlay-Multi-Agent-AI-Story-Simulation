/**
 * useSimulation — owns all simulation state and action dispatchers.
 *
 * Consumes the WS subscription API to register typed message handlers.
 * Exposes state and action functions to the rest of the UI via context.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

const AUTO_TURN_DELAY = parseInt(import.meta.env.VITE_AUTO_TURN_DELAY ?? '3200', 10)

export function useSimulation(send, subscribe) {
  const [messages,   setMessages]   = useState([{ type: 'action', content: '[SYSTEM]: Ready — press ▶ Start Scene to begin.' }])
  const [monologues, setMonologues] = useState([])
  const [insights,   setInsights]   = useState([])
  const [vitals,     setVitals]     = useState({ tension: 0.5, turn_count: 0 })
  const [world,      setWorld]      = useState({ location: 'Unknown', lighting: 'Unknown', props: [] })
  const [agents,     setAgents]     = useState([])

  const autoRef  = useRef(false)
  const isProcessingRef = useRef(false)
  const timerRef = useRef(null)
  const countdownIntervalRef = useRef(null)

  const [auto, _setAuto] = useState(false)
  const [autoDelay, _setAutoDelay] = useState(AUTO_TURN_DELAY)
  const autoDelayRef = useRef(AUTO_TURN_DELAY)
  const [isProcessing, setIsProcessing] = useState(false)
  const [autoCountdown, setAutoCountdown] = useState(null)

  const clearAutoTimers = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
      countdownIntervalRef.current = null
    }
    setAutoCountdown(null)
  }, [])

  const scheduleNextAutoTurn = useCallback((delayMs) => {
    clearAutoTimers()
    if (!autoRef.current) return

    const delay = delayMs ?? autoDelayRef.current
    let remaining = Math.max(1, Math.round(delay / 1000))
    setAutoCountdown(remaining)

    countdownIntervalRef.current = setInterval(() => {
      remaining -= 1
      if (remaining > 0) {
        setAutoCountdown(remaining)
      } else {
        if (countdownIntervalRef.current) {
          clearInterval(countdownIntervalRef.current)
          countdownIntervalRef.current = null
        }
        setAutoCountdown(null)
      }
    }, 1000)

    timerRef.current = setTimeout(() => {
      clearAutoTimers()
      if (autoRef.current && !isProcessingRef.current) {
        isProcessingRef.current = true
        setIsProcessing(true)
        send({ type: 'next_turn' })
      }
    }, delay)
  }, [clearAutoTimers, send])

  const setAuto = useCallback((val) => {
    autoRef.current = val
    _setAuto(val)
    if (val) {
      if (!isProcessingRef.current) {
        scheduleNextAutoTurn(800)
      }
    } else {
      clearAutoTimers()
    }
  }, [clearAutoTimers, scheduleNextAutoTurn])

  const setAutoPacing = useCallback((ms) => {
    autoDelayRef.current = ms
    _setAutoDelay(ms)
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
        if (d.content && (d.content.includes('Triggering AI turn') || d.content.includes('already in progress'))) {
          isProcessingRef.current = true
          setIsProcessing(true)
          clearAutoTimers()
        }
      }),
      subscribe('monologue', (d) => {
        setMonologues((p) => [...p, d])
      }),
      subscribe('world_update',  (d) => setWorld(d.world)),
      subscribe('agents_update', (d) => setAgents(d.agents)),
      subscribe('insight_update', (d) => {
        setInsights((p) => [...p, d])
      }),
      subscribe('history_reset', (d) => {
        setMessages(d.messages ?? [])
        setMonologues(d.monologues ?? [])
        setInsights([])
      }),
      subscribe('vitals_update', (d) => {
        setVitals((prev) => ({ ...prev, ...d.vitals }))
        isProcessingRef.current = false
        setIsProcessing(false)
        if (autoRef.current) {
          scheduleNextAutoTurn(autoDelayRef.current)
        }
      }),
      subscribe('download', (d) => triggerDownload(d.filename, d.content)),
      subscribe('error', (d) => {
        console.error('[WS Error]', d.code, d.detail)
        isProcessingRef.current = false
        setIsProcessing(false)
        clearAutoTimers()
        setMessages((p) => [...p, {
          type: 'action',
          content: `[ERROR]: ${d.detail}`,
        }])
      }),
    ]
    return () => {
      unsubs.forEach((u) => u())
      clearAutoTimers()
    }
  }, [subscribe, send, triggerDownload, clearAutoTimers, scheduleNextAutoTurn])

  // ── Action dispatchers ─────────────────────────────────────────────────────
  const startScene    = useCallback(() => send({ type: 'start_scene' }), [send])
  const stopScene     = useCallback(() => { 
    setAuto(false)
    clearAutoTimers()
    isProcessingRef.current = false
    setIsProcessing(false)
    send({ type: 'stop_scene' }) 
  }, [send, setAuto, clearAutoTimers])
  const nextTurn      = useCallback(() => {
    clearAutoTimers()
    isProcessingRef.current = true
    setIsProcessing(true)
    send({ type: 'next_turn' })
  }, [send, clearAutoTimers])
  const retakeTurn    = useCallback(() => {
    clearAutoTimers()
    isProcessingRef.current = true
    setIsProcessing(true)
    send({ type: 'retake_turn' })
  }, [send, clearAutoTimers])
  const exportScript  = useCallback(() => send({ type: 'export_script' }), [send])
  const injectChaos   = useCallback((command) => send({ type: 'director_command', command }), [send])
  const whisperDirective = useCallback((agent_id, whisper) => send({
    type: 'director_whisper',
    agent_id,
    whisper,
  }), [send])
  const forceEmotion  = useCallback((agent_id, emotion, value) => send({ type: 'force_emotion', agent_id, emotion, value }), [send])
  const forceRelationship = useCallback((source_agent, target_agent, metric, value) => send({
    type: 'force_relationship',
    source_agent,
    target_agent,
    metric,
    value,
  }), [send])
  const configureScene = useCallback((agents, metadata = {}) => send({
    type: 'configure_scene',
    agents,
    scene_name: metadata.sceneName,
    location: metadata.location,
    lighting: metadata.lighting,
    props: metadata.props,
  }), [send])
  const systemReset   = useCallback(() => send({ type: 'system_reset' }), [send])
  const checkModel    = useCallback((agent_id, llm_config) => send({ type: 'check_model', agent_id, llm_config }), [send])
  const sendManualDialogue = useCallback((agent_id, content, trigger_response = true) => {
    setAuto(false)
    clearAutoTimers()
    if (trigger_response) {
      isProcessingRef.current = true
      setIsProcessing(true)
    }
    send({
      type: 'manual_dialogue',
      agent_id,
      content,
      trigger_response,
    })
  }, [send, clearAutoTimers, setAuto])
  const pause         = useCallback(() => {
    setAuto(false)
    clearAutoTimers()
    isProcessingRef.current = false
    setIsProcessing(false)
    send({ type: 'pause_scene' })
  }, [setAuto, clearAutoTimers, send])

  const turnCount    = vitals.turn_count ?? 0

  return {
    // State
    messages, monologues, insights, vitals, world, agents,
    auto, setAuto, autoDelay, setAutoPacing, isProcessing, autoCountdown,
    turnCount,
    // Actions
    startScene, stopScene, nextTurn, retakeTurn, exportScript,
    injectChaos, whisperDirective, sendManualDialogue,
    forceEmotion, forceRelationship,
    configureScene, checkModel, pause, systemReset,
  }
}

