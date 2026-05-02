import { useEffect, useRef } from 'react'
import { useSimulationContext } from '../../context/SimulationContext'
import { MessageItem } from './MessageItem'

export function MessageFeed() {
  const { messages } = useSimulationContext()
  const feedRef = useRef(null)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div className="feed" ref={feedRef}>
      {messages.map((m, i) => (
        <MessageItem key={i} message={m} />
      ))}
    </div>
  )
}
