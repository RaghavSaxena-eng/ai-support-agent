import { useEffect, useRef, useState } from 'react'
import ToolSteps from './components/ToolSteps'
import DemoPanel from './components/DemoPanel'

const API = import.meta.env.VITE_API_URL || ''

const WELCOME = {
  role: 'assistant',
  text: "Hi! I'm the Acme Gadgets support assistant. I can track or cancel orders, answer questions about returns and shipping, or raise a ticket for our team.",
  steps: [],
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showDemo, setShowDemo] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(text) {
    const message = text.trim()
    if (!message || loading) return

    // history = everything except the welcome message and error bubbles
    const history = messages
      .filter((m) => m !== WELCOME && !m.error)
      .map(({ role, text }) => ({ role, text }))

    setInput('')
    setShowDemo(false)
    setMessages((prev) => [...prev, { role: 'user', text: message }])
    setLoading(true)

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
      })
      if (!res.ok) throw new Error(`Server error (${res.status})`)
      const data = await res.json()
      setMessages((prev) => [...prev, { role: 'assistant', text: data.reply, steps: data.steps }])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: `Something went wrong: ${err.message}. Is the backend running?`, error: true },
      ])
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setMessages([WELCOME])
    setInput('')
  }

  return (
    <div className="page">
      <div className="shell">
        <header className="header">
          <div className="header-left">
            <img src="/favicon.svg" alt="" width="34" height="34" />
            <div>
              <div className="title">Acme Support</div>
              <div className="status">
                <span className="dot" /> AI agent<span className="status-extra"> · Gemini function calling</span>
              </div>
            </div>
          </div>
          <div className="header-actions">
            <button className="ghost-btn demo-toggle" onClick={() => setShowDemo((v) => !v)}>
              Demo data
            </button>
            <button className="ghost-btn" onClick={reset} title="Start a new conversation">
              New chat
            </button>
          </div>
        </header>

        <div className="body">
          <main className="conversation">
            <div className="messages">
              {messages.map((m, i) => (
                <div key={i} className={`row ${m.role}`}>
                  <div className="message">
                    {m.steps?.length > 0 && <ToolSteps steps={m.steps} />}
                    <div className={`bubble ${m.error ? 'error' : ''}`}>{m.text}</div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="row assistant">
                  <div className="bubble thinking">
                    <span className="pulse" /> Working on it…
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <form
              className="composer"
              onSubmit={(e) => {
                e.preventDefault()
                send(input)
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message…"
                maxLength={2000}
                autoFocus
              />
              <button type="submit" disabled={!input.trim() || loading} aria-label="Send">
                <svg width="18" height="18" viewBox="0 0 20 20"><path d="M3 10l14-6-6 14-2-6z" fill="currentColor" /></svg>
              </button>
            </form>
          </main>

          <DemoPanel open={showDemo} onClose={() => setShowDemo(false)} onTry={send} />
        </div>
      </div>
    </div>
  )
}
