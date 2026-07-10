import { Auth0Provider, useAuth0 } from '@auth0/auth0-react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { useEffect } from 'react'
import Chat from './pages/Chat'
import ChatLab from './pages/ChatLab'
import Calculator from './pages/Calculator'
import Settings from './pages/Settings'
import { setAccessTokenGetter } from './api'
import './index.css'

const domain = import.meta.env.VITE_AUTH0_DOMAIN
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID
const audience = import.meta.env.VITE_AUTH0_AUDIENCE

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      loginWithRedirect()
    }
  }, [isLoading, isAuthenticated])

  if (isLoading || !isAuthenticated) {
    return <div className="flex items-center justify-center h-screen text-gray-500">Redirecting to login...</div>
  }

  return <>{children}</>
}

function AppShell() {
  const { logout, getAccessTokenSilently } = useAuth0()

  useEffect(() => {
    setAccessTokenGetter(() => getAccessTokenSilently({ authorizationParams: { audience } }))
  }, [getAccessTokenSilently])

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
            <button onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })} className="text-gray-400 hover:text-gray-700 text-xs ml-2">Keluar</button>
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
      <Auth0Provider
        domain={domain}
        clientId={clientId}
        authorizationParams={{
          redirect_uri: window.location.origin,
          audience,
        }}
      >
        <Routes>
          <Route path="/*" element={<AppShell />} />
        </Routes>
      </Auth0Provider>
    </BrowserRouter>
  )
}
