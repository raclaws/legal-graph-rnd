import { LogtoProvider, useLogto, useHandleSignInCallback } from '@logto/react'
import type { LogtoConfig } from '@logto/react'
import { BrowserRouter, Routes, Route, Link, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import Chat from './pages/Chat'
import ChatLab from './pages/ChatLab'
import Calculator from './pages/Calculator'
import Settings from './pages/Settings'
import { setAccessTokenGetter } from './api'
import './index.css'

const logtoConfig: LogtoConfig = {
  endpoint: 'https://i8a3uv.logto.app/',
  appId: '78s9jpal807pel5bgj88k',
}

function Callback() {
  const navigate = useNavigate()
  const { isLoading } = useHandleSignInCallback(() => navigate('/'))

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen text-gray-500">Signing in...</div>
  }
  return null
}

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, signIn } = useLogto()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      signIn(window.location.origin + '/callback')
    }
  }, [isLoading, isAuthenticated])

  if (isLoading || !isAuthenticated) {
    return <div className="flex items-center justify-center h-screen text-gray-500">Redirecting to login...</div>
  }

  return <>{children}</>
}

function AppShell() {
  const { signOut, getAccessToken } = useLogto()

  useEffect(() => {
    setAccessTokenGetter(() => getAccessToken())
  }, [getAccessToken])

  return (
    <AuthGate>
      <div className="min-h-screen bg-gray-50">
        <header className="border-b border-gray-200 bg-white px-4 py-3 flex items-center justify-between">
          <Link to="/" className="font-semibold text-gray-900">HR Compliance</Link>
          <nav className="flex gap-4 text-sm items-center">
            <Link to="/" className="text-gray-600 hover:text-gray-900">Chat</Link>
            <Link to="/lab" className="text-gray-600 hover:text-gray-900">Lab</Link>
            <Link to="/calculator" className="text-gray-600 hover:text-gray-900">Pesangon</Link>
            <Link to="/settings" className="text-gray-600 hover:text-gray-900">Settings</Link>
            <button onClick={() => signOut(window.location.origin)} className="text-gray-400 hover:text-gray-700 text-xs ml-2">Keluar</button>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/lab" element={<ChatLab />} />
          <Route path="/calculator" element={<Calculator />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </AuthGate>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <LogtoProvider config={logtoConfig}>
        <Routes>
          <Route path="/callback" element={<Callback />} />
          <Route path="/*" element={<AppShell />} />
        </Routes>
      </LogtoProvider>
    </BrowserRouter>
  )
}
