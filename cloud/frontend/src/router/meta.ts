export interface AppRouteMeta {
  guest?: boolean
  requiresAuth?: boolean
  organisationScoped?: boolean
  platformOnly?: boolean
  tenantAdminOnly?: boolean
  organisationManagerOnly?: boolean
  platformAdminAllowed?: boolean
  usersOnly?: boolean
}

declare module 'vue-router' {
  interface RouteMeta extends AppRouteMeta {}
}
