import { useState, useRef, useEffect } from 'react'
import type { ChatMessage } from '../api'

interface Props {
  chatHistory: ChatMessage[]
  onSend: (message: string) => void
}

export default function ChatPanel({ chatHistory, onSend }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  function handleSend() {
    if (!input.trim()) return
    onSend(input.trim())
    setInput('')
  }

  return (
    <div className="chat-panel">
      <div className="tutor-header">
        <span className="tutor-dot" /> AI Tutor
      </div>

      <div className="chat-messages">
        {chatHistory.length === 0 ? (
          <div className="chat-empty">
            <b>Have a question about your content?</b>
            Ask anything and get instant, grounded answers based on what you summarized.
          </div>
        ) : (
          chatHistory.map((msg, i) => (
            <div key={i} className={`chat-msg ${msg.role}`}>
              {msg.content}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          placeholder="Ask AI assistant..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSend() }}
        />
        <button className="btn" disabled={!input.trim()} onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  )
}
