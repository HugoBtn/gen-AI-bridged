import { useState, useRef, useEffect } from 'react'
import { Send, Bot } from 'lucide-react'
import Message from './Message'

const SUGGESTIONS = ['find a Director', 'find a Manager', 'who works in Sales']

export default function ChatPanel({ messages, loading, onSend }) {
  const [input, setInput] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  function submit(e) {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return
    onSend(q)
    setInput('')
  }

  return (
    <aside className="chat">
      <header className="chat__header">
        <Bot size={20} />
        <div>
          <div className="chat__title">Assistant</div>
          <div className="chat__subtitle">Find people across your sources</div>
        </div>
      </header>

      <div className="chat__messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        {loading && (
          <div className="msg msg--bot">
            <div className="msg__avatar msg__avatar--bot">
              <Bot size={16} />
            </div>
            <div className="msg__bubble msg__bubble--typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
      </div>

      <div className="chat__suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="chip" onClick={() => onSend(s)} disabled={loading}>
            {s}
          </button>
        ))}
      </div>

      <form className="chat__input" onSubmit={submit}>
        <input
          type="text"
          placeholder="Ask to find someone…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="chat__send"
          disabled={loading || !input.trim()}
          aria-label="Send"
        >
          <Send size={18} />
        </button>
      </form>
    </aside>
  )
}
