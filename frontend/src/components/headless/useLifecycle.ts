import { useEffect } from 'react'
import { useProtocol } from './useProtocol'

type LifecycleState = 'mount' | 'active' | 'dismissing' | 'gone'
type LifecycleEvent = 'mounted' | 'timeout' | 'user-dismiss'

const lifecycle = {
  id: 'lifecycle',
  initial: 'mount' as LifecycleState,
  transition(state: LifecycleState, event: LifecycleEvent): LifecycleState {
    switch (state) {
      case 'mount': return event === 'mounted' ? 'active' : state
      case 'active':
        if (event === 'timeout' || event === 'user-dismiss') return 'dismissing'
        return state
      case 'dismissing': return 'gone'
      case 'gone': return state
      default: return state
    }
  },
}

export function useLifecycle(options?: { autoDismissMs?: number }) {
  const [state, send] = useProtocol(lifecycle)

  useEffect(() => {
    send('mounted')
  }, [send])

  useEffect(() => {
    if (state === 'active' && options?.autoDismissMs) {
      const t = setTimeout(() => send('timeout'), options.autoDismissMs)
      return () => clearTimeout(t)
    }
  }, [state, options?.autoDismissMs, send])

  return {
    state,
    isVisible: state === 'active' || state === 'mount',
    dismiss: () => send('user-dismiss'),
    getProps: () => ({
      'aria-live': 'polite' as const,
      'aria-hidden': state === 'gone',
    }),
  }
}
