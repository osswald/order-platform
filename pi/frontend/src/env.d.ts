/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_ANDROID_APP?: string
  readonly VITE_APP_VERSION?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface AndroidBridgeResult {
  ok?: boolean
  error?: string
  [key: string]: unknown
}

interface Window {
  AndroidPrinter?: Record<string, (...args: unknown[]) => unknown>
  AndroidTerminal?: Record<string, (...args: unknown[]) => unknown>
  AndroidInsets?: {
    getSystemBarInsetsJson?: () => string
  }
}

declare module '@vendiqo/frontend-shared/useAppVersion' {
  import type { ComputedRef } from 'vue'
  export function useAppVersion(): {
    version: string
    buildTime: string
    label: ComputedRef<string>
  }
}
