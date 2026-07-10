import { useState, useEffect } from 'react'
import { authHeaders } from '../api'

export default function Settings() {
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [models, setModels] = useState<string[]>([])
  const [loadingModels, setLoadingModels] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    async function load() {
      const headers = await authHeaders()
      fetch('/api/settings', { headers })
        .then(r => r.json())
        .then(data => {
          setModel(data.model || '')
          setBaseUrl(data.base_url || '')
        })
      fetch('/api/settings/models', { headers })
        .then(r => r.json())
        .then(data => setModels(data.models || []))
        .finally(() => setLoadingModels(false))
    }
    load()
  }, [])

  async function handleSave() {
    setSaving(true)
    setSaved(false)
    const headers = await authHeaders()
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ model, base_url: baseUrl }),
    })
    if (res.ok) {
      const data = await res.json()
      setModel(data.model)
      setBaseUrl(data.base_url)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    }
    setSaving(false)
  }

  async function refreshModels() {
    setLoadingModels(true)
    const headers = await authHeaders()
    fetch('/api/settings/models', { headers })
      .then(r => r.json())
      .then(data => setModels(data.models || []))
      .finally(() => setLoadingModels(false))
  }

  const isCustomModel = models.length > 0 && !models.includes(model)

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <h1 className="text-lg font-semibold text-gray-900 mb-6">LLM Settings</h1>

      <div className="space-y-5">
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">Model</label>
            <button
              onClick={refreshModels}
              disabled={loadingModels}
              className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
            >
              {loadingModels ? 'Loading...' : 'Refresh'}
            </button>
          </div>
          {models.length > 0 ? (
            <select
              value={isCustomModel ? '__custom' : model}
              onChange={e => {
                if (e.target.value !== '__custom') setModel(e.target.value)
              }}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {models.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
              {isCustomModel && <option value="__custom">{model} (custom)</option>}
            </select>
          ) : (
            <input
              type="text"
              value={model}
              onChange={e => setModel(e.target.value)}
              placeholder="e.g. claude-sonnet-4-20250514"
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          )}
          {isCustomModel && (
            <input
              type="text"
              value={model}
              onChange={e => setModel(e.target.value)}
              className="mt-2 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
          <input
            type="text"
            value={baseUrl}
            onChange={e => setBaseUrl(e.target.value)}
            placeholder="https://api.anthropic.com"
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-400 mt-1">Leave default for Anthropic direct. Change for gateways/proxies.</p>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          {saved && <span className="text-sm text-green-600">Saved</span>}
        </div>
      </div>
    </div>
  )
}
