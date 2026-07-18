import { useProtocol } from './useProtocol'

type EditState = 'idle' | 'editing' | 'dirty'
type EditEvent = 'focus' | 'input' | 'commit' | 'cancel'

const editCommit = {
  id: 'edit-commit',
  initial: 'idle' as EditState,
  transition(state: EditState, event: EditEvent): EditState {
    switch (state) {
      case 'idle': return event === 'focus' ? 'editing' : state
      case 'editing': return event === 'input' ? 'dirty' : event === 'cancel' ? 'idle' : state
      case 'dirty':
        if (event === 'commit') return 'idle'
        if (event === 'cancel') return 'idle'
        if (event === 'input') return 'dirty'
        return state
      default: return state
    }
  },
}

export function useEditCommit() {
  const [state, send] = useProtocol(editCommit)

  return {
    state,
    isDirty: state === 'dirty',
    isEditing: state === 'editing' || state === 'dirty',
    focus: () => send('focus'),
    input: () => send('input'),
    commit: () => send('commit'),
    cancel: () => send('cancel'),
    getFieldProps: () => ({
      'aria-readonly': state === 'idle',
      onFocus: () => send('focus'),
      onChange: () => send('input'),
    }),
  }
}
