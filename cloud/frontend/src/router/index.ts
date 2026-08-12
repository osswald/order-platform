import './meta'
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import { i18n } from '../i18n'
import { listDetailRoutes } from '../composables/useListDetailRouting'
import { isAuthSessionActive } from '@/api'

const orgScoped = { requiresAuth: true, organisationScoped: true }
const platformOnly = { requiresAuth: true, platformOnly: true }
const tenantAdminOnly = { requiresAuth: true, tenantAdminOnly: true }
const organisationManagerOnly = { requiresAuth: true, organisationManagerOnly: true }
const usersOnly = { requiresAuth: true, usersOnly: true }
const authOnly = { requiresAuth: true }

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../components/LoginPage.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    redirect: { name: 'dashboard' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../components/Dashboard.vue'),
    meta: orgScoped,
  },
  {
    path: '/first-event-setup',
    name: 'first-event-setup',
    component: () => import('../components/FirstEventSetupWizard.vue'),
    meta: orgScoped,
  },
  ...listDetailRoutes({
    path: '/events',
    listName: 'events',
    component: () => import('../components/Events.vue'),
    meta: orgScoped,
  }),
  {
    path: '/events/import/orderjutsu',
    name: 'events-import-orderjutsu',
    component: () => import('../components/OrderjutsuImportWizard.vue'),
    meta: { ...organisationManagerOnly, platformAdminAllowed: true },
  },
  {
    path: '/events/:id(\\d+)/stats',
    name: 'events-stats',
    component: () => import('../components/EventStatsPage.vue'),
    meta: orgScoped,
  },
  ...listDetailRoutes({
    path: '/waiters',
    listName: 'waiters',
    component: () => import('../components/Waiters.vue'),
    meta: orgScoped,
  }),
  ...listDetailRoutes({
    path: '/articles',
    listName: 'articles',
    component: () => import('../components/Articles.vue'),
    meta: orgScoped,
  }),
  ...listDetailRoutes({
    path: '/article-categories',
    listName: 'article-categories',
    component: () => import('../components/ArticleCategories.vue'),
    meta: orgScoped,
  }),
  ...listDetailRoutes({
    path: '/ingredients',
    listName: 'ingredients',
    component: () => import('../components/Ingredients.vue'),
    meta: orgScoped,
  }),
  {
    path: '/appliance-lendings',
    name: 'appliance-lendings',
    component: () => import('../components/ApplianceLendings.vue'),
    meta: orgScoped,
  },
  {
    path: '/sumup-devices',
    name: 'sumup-devices',
    component: () => import('../components/SumupDevices.vue'),
    meta: organisationManagerOnly,
  },
  {
    path: '/sumup/oauth/callback',
    name: 'sumup-oauth-callback',
    component: () => import('../components/SumupOAuthCallback.vue'),
    meta: organisationManagerOnly,
  },
  ...listDetailRoutes({
    path: '/verleiher',
    listName: 'hire-companies',
    component: () => import('../components/HireCompanies.vue'),
    meta: platformOnly,
  }),
  ...listDetailRoutes({
    path: '/organisations',
    listName: 'organisations',
    component: () => import('../components/Organisations.vue'),
    meta: organisationManagerOnly,
    createMeta: tenantAdminOnly,
  }),
  {
    path: '/verleiher-einstellungen',
    name: 'tenant-settings',
    component: () => import('../components/TenantSettings.vue'),
    meta: tenantAdminOnly,
  },
  ...listDetailRoutes({
    path: '/appliances',
    listName: 'appliances',
    component: () => import('../components/Appliances.vue'),
    meta: tenantAdminOnly,
  }),
  {
    path: '/rentals',
    name: 'rentals',
    component: () => import('../components/RentalsCalendar.vue'),
    meta: tenantAdminOnly,
  },
  ...listDetailRoutes({
    path: '/users',
    listName: 'users',
    component: () => import('../components/Users.vue'),
    meta: usersOnly,
  }),
  ...listDetailRoutes({
    path: '/countries',
    listName: 'countries',
    component: () => import('../components/Countries.vue'),
    meta: authOnly,
  }),
  ...listDetailRoutes({
    path: '/tax-codes',
    listName: 'tax-codes',
    component: () => import('../components/TaxCodes.vue'),
    meta: authOnly,
  }),
  ...listDetailRoutes({
    path: '/payment-types',
    listName: 'payment-types',
    component: () => import('../components/PaymentTypes.vue'),
    meta: authOnly,
  }),
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../components/AccountSettings.vue'),
    meta: orgScoped,
  },
  {
    path: '/help',
    name: 'help',
    component: () => import('../components/HelpCenter.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/help/:slug',
    name: 'help-article',
    component: () => import('../components/HelpCenter.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/no-access/:section',
    name: 'no-access',
    component: () => import('../components/SectionPlaceholder.vue'),
    props: (route: RouteLocationNormalizedLoaded) => ({
      title: i18n.global.t('noAccess.title'),
      description:
        route.params.section === 'users'
          ? i18n.global.t('noAccess.usersDescription')
          : i18n.global.t('noAccess.defaultDescription'),
    }),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'dashboard' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const isLoggedIn = isAuthSessionActive()

  if (to.meta.guest) {
    if (isLoggedIn) {
      return next({ name: 'dashboard', query: to.query })
    }
    return next()
  }

  if (to.meta.requiresAuth && !isLoggedIn) {
    return next({
      name: 'login',
      query: { redirect: to.fullPath },
    })
  }

  next()
})
