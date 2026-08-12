import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppNavMenu from './AppNavMenu.vue'
import de from '../locales/de.json'
import { vuetifyStubs } from '../../tests/helpers/vuetifyStub.js'

const i18n = createI18n({
  legacy: false,
  locale: 'de',
  messages: { de },
})

async function mountNav(props: {
  canAccessTenantAdmin?: boolean
  isPlatformAdmin?: boolean
}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/dashboard', name: 'dashboard', component: { template: '<div />' } },
      { path: '/appliances', name: 'appliances', component: { template: '<div />' } },
      { path: '/rentals', name: 'rentals', component: { template: '<div />' } },
      { path: '/verleiher-einstellungen', name: 'tenant-settings', component: { template: '<div />' } },
      { path: '/hire-companies', name: 'hire-companies', component: { template: '<div />' } },
    ],
  })
  await router.push('/dashboard')
  await router.isReady()
  return mount(AppNavMenu, {
    props: {
      canAccessTenantAdmin: false,
      isPlatformAdmin: false,
      ...props,
    },
    global: {
      plugins: [router, i18n],
      stubs: {
        ...vuetifyStubs(),
        'v-list': { template: '<div><slot /></div>' },
        'v-list-item': {
          props: ['to', 'title', 'prependIcon'],
          template: '<a class="nav-item" :data-title="title">{{ title }}</a>',
        },
        'v-select': { template: '<div />' },
      },
    },
  })
}

describe('AppNavMenu rentals access', () => {
  it('shows Ausleihe for tenant admins', async () => {
    const wrapper = await mountNav({ canAccessTenantAdmin: true })
    const titles = wrapper.findAll('.nav-item').map((el) => el.attributes('data-title'))
    expect(titles).toContain('Ausleihe')
    expect(titles).toContain('Geräte')
  })

  it('hides Ausleihe for organisation users', async () => {
    const wrapper = await mountNav({ canAccessTenantAdmin: false })
    const titles = wrapper.findAll('.nav-item').map((el) => el.attributes('data-title'))
    expect(titles).not.toContain('Ausleihe')
    expect(titles).not.toContain('Geräte')
  })

  it('shows Verleiher-Einstellungen for platform admins with tenant access', async () => {
    const wrapper = await mountNav({
      isPlatformAdmin: true,
      canAccessTenantAdmin: true,
    })
    const titles = wrapper.findAll('.nav-item').map((el) => el.attributes('data-title'))
    expect(titles).toContain('Verleiher')
    expect(titles).toContain('Verleiher-Einstellungen')
  })

  it('hides Verleiher-Einstellungen without tenant admin access', async () => {
    const wrapper = await mountNav({
      isPlatformAdmin: true,
      canAccessTenantAdmin: false,
    })
    const titles = wrapper.findAll('.nav-item').map((el) => el.attributes('data-title'))
    expect(titles).toContain('Verleiher')
    expect(titles).not.toContain('Verleiher-Einstellungen')
  })
})
