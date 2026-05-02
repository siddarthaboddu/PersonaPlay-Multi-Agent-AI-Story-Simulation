/**
 * useWebSocket — manages the WebSocket lifecycle with exponential backoff reconnection.
 *
 * Returns:
 *   isConnected  — boolean connection status
 *   send(obj)    — send a JSON message (no-op if disconnected)
 *   subscribe    — register a handler for a specific message type
 *                  (returns an unsubscribe function)
 */
import { useCallback, useEffect, useRef, useState } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws'
const MAX_RETRY_DELAY_MS = 30_000

export function useWebSocket() {
  const wsRef        = useRef(null)
  const retryCount   = useRef(0)
  const retryTimer   = useRef(null)
  const handlersRef  = useRef({})  // { messageType: Set<handler> }
  const [isConnected, setIsConnected] = useState(false)

  const dispatch = useCallback((data) => {
    const handlers = handlersRef.current[data.type]
    if (handlers) handlers.forEach((h) => h(data))
    // Wildcard handlers (registered with type '*')
    const wildcards = handlersRef.current['*']
    if (wildcards) wildcards.forEach((h) => h(data))
  }, [])

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) return

    const sock = new WebSocket(WS_URL)
    wsRef.current = sock

    sock.onopen = () => {
      setIsConnected(true)
      retryCount.current = 0
      sock.send(JSON.stringify({ type: 'get_state' }))
    }

    sock.onmessage = (ev) => {
      try {
        dispatch(JSON.parse(ev.data))
      } catch (e) {
        console.error('[WS] Failed to parse message:', e)
      }
    }

    sock.onclose = () => {
      setIsConnected(false)
      wsRef.current = null
      // Exponential backoff: 1s, 2s, 4s … capped at 30s
      const delay = Math.min(1000 * 2 ** retryCount.current, MAX_RETRY_DELAY_MS)
      retryCount.current++
      console.log(`[WS] Reconnecting in ${delay}ms (attempt ${retryCount.current})…`)
      retryTimer.current = setTimeout(connect, delay)
    }

    sock.onerror = () => {
      sock.close()
    }
  }, [dispatch])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryTimer.current)
      if (wsRef.current) {
        wsRef.current.onopen = null
        wsRef.current.onmessage = null
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const send = useCallback((obj) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(obj))
    }
  }, [])

  /**
   * Register a handler for a specific message type.
   * @param {string} type  WS message type (or '*' for all messages)
   * @param {function} handler  Called with the parsed message object
   * @returns {function}  Unsubscribe function
   */
  const subscribe = useCallback((type, handler) => {
    if (!handlersRef.current[type]) {
      handlersRef.current[type] = new Set()
    }
    handlersRef.current[type].add(handler)
    return () => handlersRef.current[type]?.delete(handler)
  }, [])

  return { isConnected, send, subscribe }
}
