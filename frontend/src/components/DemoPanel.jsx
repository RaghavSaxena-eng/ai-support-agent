const CUSTOMERS = [
  { email: 'priya@example.com', orders: 'AC1042 (shipped), AC1043 (delivered)' },
  { email: 'rahul@example.com', orders: 'AC1057 (processing), AC1061 (cancelled)' },
  { email: 'neha@example.com', orders: 'AC1066 (delivered)' },
]

const PROMPTS = [
  'Where is my order AC1042? Email is priya@example.com',
  "I want to cancel AC1057, I'm rahul@example.com",
  'How long do refunds take?',
  'My speaker from order AC1066 arrived broken. neha@example.com',
  'Can I return earbuds I already opened?',
]

export default function DemoPanel({ open, onClose, onTry }) {
  return (
    <aside className={`demo ${open ? 'open' : ''}`}>
      <div className="demo-head">
        <h2>Try it</h2>
        <button className="ghost-btn demo-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      <p className="demo-note">This is a demo store. Use these sample customers:</p>
      <ul className="customers">
        {CUSTOMERS.map((c) => (
          <li key={c.email}>
            <code>{c.email}</code>
            <span>{c.orders}</span>
          </li>
        ))}
      </ul>

      <p className="demo-note">Or start with one of these:</p>
      <div className="prompts">
        {PROMPTS.map((p) => (
          <button key={p} onClick={() => onTry(p)}>
            {p}
          </button>
        ))}
      </div>
    </aside>
  )
}
