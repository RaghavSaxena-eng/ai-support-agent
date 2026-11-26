import { useState } from 'react'

// Human-readable labels for each tool call
const LABELS = {
  get_order_status: (a) => `Looked up order ${a.order_id ?? ''}`,
  list_orders: (a) => `Listed orders for ${a.email ?? 'customer'}`,
  cancel_order: (a) => `Cancelled order ${a.order_id ?? ''}`,
  search_faq: (a) => `Searched help articles for “${a.query ?? ''}”`,
  create_ticket: () => 'Created a support ticket',
}

export default function ToolSteps({ steps }) {
  const [open, setOpen] = useState(null)

  return (
    <div className="steps">
      {steps.map((step, i) => {
        const failed = Boolean(step.result?.error)
        const label = (LABELS[step.tool] || (() => step.tool))(step.args)
        return (
          <div key={i} className={`step ${failed ? 'failed' : ''}`}>
            <button className="step-head" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
              <span className="step-icon">{failed ? '!' : '✓'}</span>
              <span className="step-label">{failed && step.tool === 'cancel_order' ? 'Tried to cancel order' : label}</span>
              <span className="step-chevron">{open === i ? '−' : '+'}</span>
            </button>
            {open === i && (
              <div className="step-detail">
                <div className="step-code-label fn">{step.tool}()</div>
                <pre>{JSON.stringify(step.args, null, 2)}</pre>
                <div className="step-code-label">result</div>
                <pre>{JSON.stringify(step.result, null, 2)}</pre>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
