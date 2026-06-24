import type { InjectionKey } from 'vue'
import type { SessionContext } from '@/types/ui'

export type { SessionContext } from '@/types/ui'

export const SESSION_CONTEXT_KEY: InjectionKey<SessionContext | null> = Symbol('sessionContext')
