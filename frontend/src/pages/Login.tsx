import { useState } from 'react'

interface Props {
  onLogin: (token: string) => void
}

export default function Login({ onLogin }: Props) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) {
        setError('Username atau password salah')
        return
      }
      const data = await res.json()
      localStorage.setItem('auth_token', data.token)
      onLogin(data.token)
    } catch {
      setError('Tidak dapat terhubung ke server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-gray-900 mb-1">HR Compliance</h1>
        <p className="text-sm text-gray-500 mb-6">Masuk untuk melanjutkan</p>

        <label className="block text-xs font-medium text-gray-700 mb-1">Username</label>
        <input
          type="text"
          value={username}
          onChange={e => setUsername(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-1 focus:ring-blue-500"
          autoFocus
        />

        <label className="block text-xs font-medium text-gray-700 mb-1">Password</label>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

        <button
          type="submit"
          disabled={loading || !username || !password}
          className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
        >
          {loading ? 'Memproses...' : 'Masuk'}
        </button>
      </form>
    </div>
  )
}
