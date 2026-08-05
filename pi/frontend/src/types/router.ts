export interface AppRouteMeta {
  title?: string
  fullscreen?: boolean
  /** Hide Android system bars (kitchen / pickup / customer display). */
  immersive?: boolean
  hideNav?: boolean
  nav?: boolean
  navLabel?: string
  requiresAdmin?: boolean
  requiresBundle?: boolean
  requiresEvent?: boolean
  requiresWaiter?: boolean
  /** Waiter or cash-register session (e.g. collective-bill routes). */
  requiresOperator?: boolean
  requiresRegister?: boolean
}

declare module 'vue-router' {
  interface RouteMeta extends AppRouteMeta {}
}
