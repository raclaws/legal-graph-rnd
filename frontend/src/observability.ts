import { onCLS, onINP, onLCP, onTTFB } from 'web-vitals'

const AXIOM_TOKEN = import.meta.env.VITE_AXIOM_TOKEN
const AXIOM_DATASET = import.meta.env.VITE_AXIOM_DATASET || 'legal-graph'

function send(events: Record<string, unknown>[]) {
  if (!AXIOM_TOKEN) return

  fetch(`https://api.axiom.co/v1/datasets/${AXIOM_DATASET}/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${AXIOM_TOKEN}`,
    },
    body: JSON.stringify(events),
    keepalive: true,
  }).catch(() => {})
}

export function initObservability() {
  if (!AXIOM_TOKEN) return

  // Web Vitals
  const reportVital = (metric: { name: string; value: number; id: string }) => {
    send([{ _time: new Date().toISOString(), type: 'web_vital', name: metric.name, value: metric.value, id: metric.id, url: location.pathname }])
  }

  onCLS(reportVital)
  onINP(reportVital)
  onLCP(reportVital)
  onTTFB(reportVital)

  // JS errors
  window.addEventListener('error', (event) => {
    send([{
      _time: new Date().toISOString(),
      type: 'js_error',
      message: event.message,
      filename: event.filename,
      line: event.lineno,
      col: event.colno,
      url: location.pathname,
    }])
  })

  window.addEventListener('unhandledrejection', (event) => {
    send([{
      _time: new Date().toISOString(),
      type: 'js_error',
      message: String(event.reason),
      url: location.pathname,
    }])
  })
}
