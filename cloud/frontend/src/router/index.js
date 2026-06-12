import { createRouter, createWebHistory } from 'vue-router'
import { i18n } from '../i18n'
import { listDetailRoutes } from '../composables/useListDetailRouting'

import Dashboard from '../components/Dashboard.vue'
import Events from '../components/Events.vue'
import Waiters from '../components/Waiters.vue'
import Articles from '../components/Articles.vue'
import ArticleCategories from '../components/ArticleCategories.vue'
import ApplianceLendings from '../components/ApplianceLendings.vue'
import Organisations from '../components/Organisations.vue'
import HireCompanies from '../components/HireCompanies.vue'
import TenantSettings from '../components/TenantSettings.vue'
import Appliances from '../components/Appliances.vue'
import Users from '../components/Users.vue'
import AccountSettings from '../components/AccountSettings.vue'
import StripeConnectReturn from '../components/StripeConnectReturn.vue'
import LoginPage from '../components/LoginPage.vue'
import SectionPlaceholder from '../components/SectionPlaceholder.vue'
import HelpCenter from '../components/HelpCenter.vue'
import Countries from '../components/Countries.vue'
import TaxCodes from '../components/TaxCodes.vue'
import PaymentTypes from '../components/PaymentTypes.vue'

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
    component: LoginPage,
    meta: { guest: true },
  },
  {
    path: '/',
    redirect: { name: 'dashboard' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: Dashboard,
    meta: orgScoped,
  },
  ...listDetailRoutes({ path: '/events', listName: 'events', component: Events, meta: orgScoped }),
  ...listDetailRoutes({ path: '/waiters', listName: 'waiters', component: Waiters, meta: orgScoped }),
  ...listDetailRoutes({ path: '/articles', listName: 'articles', component: Articles, meta: orgScoped }),
  ...listDetailRoutes({
    path: '/article-categories',
    listName: 'article-categories',
    component: ArticleCategories,
    meta: orgScoped,
  }),
  {
    path: '/appliance-lendings',
    name: 'appliance-lendings',
    component: ApplianceLendings,
    meta: orgScoped,
  },
  ...listDetailRoutes({
    path: '/verleiher',
    listName: 'hire-companies',
    component: HireCompanies,
    meta: platformOnly,
  }),
  ...listDetailRoutes({
    path: '/organisations',
    listName: 'organisations',
    component: Organisations,
    meta: organisationManagerOnly,
    createMeta: tenantAdminOnly,
  }),
  {
    path: '/verleiher-einstellungen',
    name: 'tenant-settings',
    component: TenantSettings,
    meta: tenantAdminOnly,
  },
  ...listDetailRoutes({
    path: '/appliances',
    listName: 'appliances',
    component: Appliances,
    meta: tenantAdminOnly,
  }),
  ...listDetailRoutes({ path: '/users', listName: 'users', component: Users, meta: usersOnly }),
  ...listDetailRoutes({ path: '/countries', listName: 'countries', component: Countries, meta: authOnly }),
  ...listDetailRoutes({ path: '/tax-codes', listName: 'tax-codes', component: TaxCodes, meta: authOnly }),
  ...listDetailRoutes({ path: '/payment-types', listName: 'payment-types', component: PaymentTypes, meta: authOnly }),
  {
    path: '/settings',
    name: 'settings',
    component: AccountSettings,
    meta: orgScoped,
  },
  {
    path: '/settings/stripe/return',
    name: 'stripe-connect-return',
    component: StripeConnectReturn,
    meta: tenantAdminOnly,
  },
  {
    path: '/settings/stripe/refresh',
    name: 'stripe-connect-refresh',
    component: StripeConnectReturn,
    meta: tenantAdminOnly,
  },
  {
    path: '/help',
    name: 'help',
    component: HelpCenter,
    meta: { requiresAuth: true },
  },
  {
    path: '/help/:slug',
    name: 'help-article',
    component: HelpCenter,
    meta: { requiresAuth: true },
  },
  {
    path: '/no-access/:section',
    name: 'no-access',
    component: SectionPlaceholder,
    props: (route) => ({
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
  const isLoggedIn = !!localStorage.getItem('access_token')

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
