import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from './components/Dashboard.vue'
import Events from './components/Events.vue'
import Waiters from './components/Waiters.vue'
import Articles from './components/Articles.vue'
import ArticleCategories from './components/ArticleCategories.vue'
import ApplianceLendings from './components/ApplianceLendings.vue'
import Organisations from './components/Organisations.vue'
import Appliances from './components/Appliances.vue'
import Users from './components/Users.vue'
import AccountSettings from './components/AccountSettings.vue'
import LoginPage from './components/LoginPage.vue'
import SectionPlaceholder from './components/SectionPlaceholder.vue'

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
    meta: { requiresAuth: true, organisationScoped: true },
  },
  {
    path: '/events',
    name: 'events',
    component: Events,
    meta: { requiresAuth: true, organisationScoped: true },
  },
  {
    path: '/waiters',
    name: 'waiters',
    component: Waiters,
    meta: { requiresAuth: true, organisationScoped: true },
  },
  {
    path: '/articles',
    name: 'articles',
    component: Articles,
    meta: { requiresAuth: true, organisationScoped: true },
  },
  {
    path: '/article-categories',
    name: 'article-categories',
    component: ArticleCategories,
    meta: { requiresAuth: true, organisationScoped: true },
  },
  {
    path: '/appliance-lendings',
    name: 'appliance-lendings',
    component: ApplianceLendings,
    meta: { requiresAuth: true, organisationScoped: true },
  },
  {
    path: '/organisations',
    name: 'organisations',
    component: Organisations,
    meta: { requiresAuth: true, adminOnly: true },
  },
  {
    path: '/appliances',
    name: 'appliances',
    component: Appliances,
    meta: { requiresAuth: true, adminOnly: true },
  },
  {
    path: '/users',
    name: 'users',
    component: Users,
    meta: { requiresAuth: true, adminOnly: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: AccountSettings,
    meta: { requiresAuth: true, organisationScoped: true },
  },
  {
    path: '/no-access/:section',
    name: 'no-access',
    component: SectionPlaceholder,
    props: (route) => ({
      title: 'Kein Zugriff',
      description:
        route.params.section === 'users'
          ? 'Nur Administratoren können Benutzerkonten anzeigen und verwalten.'
          : 'Nur Administratoren können diesen Bereich anzeigen und verwalten.',
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

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const isLoggedIn = !!token

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
