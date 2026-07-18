import { useProtocol } from './useProtocol'

type NavigationState = { focused: number; count: number }
type NavigationEvent = 'next' | 'prev' | 'first' | 'last' | { type: 'set-count'; count: number } | { type: 'focus'; index: number }

const navigation = {
  id: 'navigation',
  initial: { focused: -1, count: 0 } as NavigationState,
  transition(state: NavigationState, event: NavigationEvent): NavigationState {
    if (typeof event === 'object') {
      if (event.type === 'set-count') return { ...state, count: event.count }
      if (event.type === 'focus') return { ...state, focused: event.index }
    }
    const { focused, count } = state
    if (count === 0) return state
    switch (event) {
      case 'next': return { ...state, focused: (focused + 1) % count }
      case 'prev': return { ...state, focused: (focused - 1 + count) % count }
      case 'first': return { ...state, focused: 0 }
      case 'last': return { ...state, focused: count - 1 }
      default: return state
    }
  },
}

export function useNavigation(count: number) {
  const [state, send] = useProtocol(navigation)

  if (state.count !== count) {
    send({ type: 'set-count', count })
  }

  return {
    focused: state.focused,
    next: () => send('next'),
    prev: () => send('prev'),
    first: () => send('first'),
    last: () => send('last'),
    focus: (index: number) => send({ type: 'focus', index }),
    getItemProps: (index: number) => ({
      'aria-selected': state.focused === index,
      tabIndex: state.focused === index ? 0 : -1,
      onFocus: () => send({ type: 'focus', index }),
    }),
    getContainerProps: () => ({
      role: 'listbox' as const,
      'aria-activedescendant': state.focused >= 0 ? `item-${state.focused}` : undefined,
      onKeyDown: (e: React.KeyboardEvent) => {
        if (e.key === 'ArrowDown') { e.preventDefault(); send('next') }
        else if (e.key === 'ArrowUp') { e.preventDefault(); send('prev') }
        else if (e.key === 'Home') { e.preventDefault(); send('first') }
        else if (e.key === 'End') { e.preventDefault(); send('last') }
      },
    }),
  }
}
