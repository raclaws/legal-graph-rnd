import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Chat from './pages/Chat'
import ChatLab from './pages/ChatLab'
import Calculator from './pages/Calculator'
import Settings from './pages/Settings'
import Login from './pages/Login'
import './index.css'

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('auth_token'))
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    if (!token) { setChecking(false); return }
    fetch('/api/auth/check', { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        if (!res.ok) {
          localStorage.removeItem('auth_token')
          setToken(null)
        }
      })
      .catch(() => {})
      .finally(() => setChecking(false))
  }, [])

  if (checking) return null

  if (!token) return <Login onLogin={setToken} />

  function handleLogout() {
    localStorage.removeItem('auth_token')
    setToken(null)
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="border-b border-gray-200 bg-white px-4 py-3 flex items-center justify-between">
          <Link to="/" className="font-semibold text-gray-900">HR Compliance</Link>
          <nav className="flex gap-4 text-sm items-center">
            <Link to="/" className="text-gray-600 hover:text-gray-900">Chat</Link>
            <Link to="/lab" className="text-gray-600 hover:text-gray-900">Lab</Link>
            <Link to="/calculator" className="text-gray-600 hover:text-gray-900">Pesangon</Link>
            <Link to="/settings" className="text-gray-600 hover:text-gray-900">Settings</Link>
            <button onClick={handleLogout} className="text-gray-400 hover:text-gray-700 text-xs ml-2">Keluar</button>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/lab" element={<ChatLab />} />
          <Route path="/calculator" element={<Calculator />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
