interface Props {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatMessage({ role, content }: Props) {
  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-gray-900 text-white rounded-2xl rounded-br-md px-4 py-2.5 max-w-[80%] text-sm">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-2.5 max-w-[80%] text-sm text-gray-700">
        {content}
      </div>
    </div>
  )
}
