import { useState, useRef } from 'react'

interface Props {
  onSend: (text: string, file?: File) => void
  disabled?: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if ((!trimmed && !file) || disabled) return
    onSend(trimmed || 'Analisis dokumen ini', file || undefined)
    setText('')
    setFile(null)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      {file && (
        <div className="flex items-center gap-2 text-xs">
          <span className="bg-blue-50 border border-blue-200 rounded-full px-3 py-1 text-blue-700 flex items-center gap-1.5">
            <span>📎</span>
            <span className="max-w-[200px] truncate">{file.name}</span>
            <button
              type="button"
              onClick={() => setFile(null)}
              className="text-blue-400 hover:text-blue-700 ml-1"
            >
              ×
            </button>
          </span>
          <span className="text-gray-400">🔒 tidak disimpan</span>
        </div>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          className="rounded-lg border border-gray-300 px-3 py-2.5 text-gray-500 hover:bg-gray-50 disabled:opacity-30"
          title="Upload dokumen"
        >
          📎
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.txt,.docx"
          className="hidden"
          onChange={e => {
            const f = e.target.files?.[0]
            if (f) setFile(f)
            e.target.value = ''
          }}
        />
        <input
          type="text"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder={file ? 'Tambah pesan (opsional)...' : 'Ketik pertanyaan HR...'}
          disabled={disabled}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || (!text.trim() && !file)}
          className="rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Kirim
        </button>
      </div>
    </form>
  )
}
