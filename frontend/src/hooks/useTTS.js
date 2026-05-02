/**
 * useTTS — Text-to-Speech synthesis for agent dialogue.
 *
 * Returns:
 *   tts        — boolean (is TTS enabled)
 *   setTts     — toggle setter
 *   speak(text, agentName) — speak text if TTS is on
 */
import { useCallback, useRef, useState } from 'react'

export function useTTS() {
  const [tts, setTts] = useState(false)
  const ttsRef = useRef(false)

  // Keep ref in sync for use inside closures (e.g., WS message handler)
  const handleSetTts = useCallback((value) => {
    ttsRef.current = value
    setTts(value)
  }, [])

  const speak = useCallback((text, agentName = '') => {
    if (!ttsRef.current || !('speechSynthesis' in window)) return
    const cleaned = text.replace(/\[.*?\]/g, '').trim()
    if (!cleaned) return
    const utterance = new SpeechSynthesisUtterance(cleaned)
    // Give each agent a subtly different pitch based on their name
    utterance.pitch = 0.8 + ((agentName.charCodeAt(0) || 65) % 8) / 18
    speechSynthesis.speak(utterance)
  }, [])

  return { tts, setTts: handleSetTts, speak }
}
