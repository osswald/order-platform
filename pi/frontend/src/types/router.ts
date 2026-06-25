export interface AppRouteMeta {
  title?: string
  fullscreen?: boolean
  hideNav?: boolean
  nav?: boolean
  navLabel?: string
  requiresAdmin?: boolean
  requiresBundle?: boolean
  requiresEvent?: boolean
  requiresWaiter?: boolean
  requiresRegister?: boolean
}

declare module 'vue-router' {
  interface RouteMeta extends AppRouteMeta {}
}
