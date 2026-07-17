interface Props {
  role: 'user' | 'assistant'
  content: string
  onRetry?: () => void
}

export default function ChatMessage({ role, content, onRetry }: Props) {
  if (role === 'user') {
    return (
      <div className="flex justify-end items-center gap-1.5 group">
        {onRetry && (
          <button
            onClick={onRetry}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-gray-100"
            title="Kirim ulang"
          >
            <svg className="w-3.5 h-3.5 text-gray-400" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2 8a6 6 0 0 1 10.3-4.2L14 2v4h-4l1.7-1.7A4.5 4.5 0 0 0 3.5 8H2zm12 0a6 6 0 0 1-10.3 4.2L2 14v-4h4l-1.7 1.7A4.5 4.5 0 0 0 12.5 8H14z" />
            </svg>
          </button>
        )}
        <div className="bg-gray-900 text-white rounded-2xl rounded-br-md px-4 py-2.5 max-w-[80%] text-sm">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] text-sm text-gray-700">
        {content}
      </div>
    </div>
  )
}
