import { useRef, useSyncExternalStore, useCallback } from 'react'

type Listener = () => void

interface ProtocolInstance<S, E> {
  getState: () => S
  subscribe: (listener: Listener) => () => void
  send: (event: E) => void
}

interface Protocol<S, E> {
  id: string
  initial: S
  transition: (state: S, event: E) => S
  guard?: (state: S, event: E) => boolean
}

function createInstance<S, E>(protocol: Protocol<S, E>): ProtocolInstance<S, E> {
  let state = protocol.initial
  const listeners = new Set<Listener>()

  return {
    getState: () => state,
    subscribe: (listener: Listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    send: (event: E) => {
      if (protocol.guard && !protocol.guard(state, event)) return
      const next = protocol.transition(state, event)
      if (next !== state) {
        state = next
        listeners.forEach(l => l())
      }
    },
  }
}

export function useProtocol<S, E>(protocol: Protocol<S, E>): [S, (event: E) => void] {
  const ref = useRef<ProtocolInstance<S, E> | null>(null)
  if (!ref.current) ref.current = createInstance(protocol)
  const instance = ref.current
  const state = useSyncExternalStore(instance.subscribe, instance.getState, instance.getState)
  const send = useCallback((event: E) => instance.send(event), [instance])
  return [state, send]
}
