import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Chat from './pages/Chat'
import Calculator from './pages/Calculator'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="border-b border-gray-200 bg-white px-4 py-3 flex items-center justify-between">
          <a href="/" className="font-semibold text-gray-900">HR Compliance</a>
          <nav className="flex gap-4 text-sm">
            <a href="/" className="text-gray-600 hover:text-gray-900">Chat</a>
            <a href="/calculator" className="text-gray-600 hover:text-gray-900">Pesangon</a>
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
