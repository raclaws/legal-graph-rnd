import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Chat from './pages/Chat'
import Calculator from './pages/Calculator'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="border-b border-gray-200 bg-white px-4 py-3 flex items-center justify-between">
          <Link to="/" className="font-semibold text-gray-900">HR Compliance</Link>
          <nav className="flex gap-4 text-sm">
            <Link to="/" className="text-gray-600 hover:text-gray-900">Chat</Link>
            <Link to="/calculator" className="text-gray-600 hover:text-gray-900">Pesangon</Link>
          </nav>
        </header>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/calculator" element={<Calculator />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
