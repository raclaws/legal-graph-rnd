import { Fragment, type ReactNode } from 'react'

function parseInline(text: string) {
  const parts: (string | ReactNode)[] = []
  const regex = /(\*\*(.+?)\*\*)|(`(.+?)`)/g
  let last = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    if (match[2]) parts.push(<strong key={match.index}>{match[2]}</strong>)
    else if (match[4]) parts.push(<code key={match.index} className="bg-gray-100 px-1 py-0.5 rounded text-xs">{match[4]}</code>)
    last = regex.lastIndex
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

export default function Markdown({ text }: { text: string }) {
  const lines = text.split('\n')

  return (
    <>
      {lines.map((line, i) => (
        <Fragment key={i}>
          {i > 0 && <br />}
          {parseInline(line)}
        </Fragment>
      ))}
    </>
  )
}
