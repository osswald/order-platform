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

async function mountNav(canAccessTenantAdmin: boolean) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/dashboard', name: 'dashboard', component: { template: '<div />' } },
      { path: '/appliances', name: 'appliances', component: { template: '<div />' } },
      { path: '/rentals', name: 'rentals', component: { template: '<div />' } },
    ],
  })
  await router.push('/dashboard')
  await router.isReady()
  return mount(AppNavMenu, {
    props: { canAccessTenantAdmin },
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
    const wrapper = await mountNav(true)
    const titles = wrapper.findAll('.nav-item').map((el) => el.attributes('data-title'))
    expect(titles).toContain('Ausleihe')
    expect(titles).toContain('Geräte')
  })

  it('hides Ausleihe for organisation users', async () => {
    const wrapper = await mountNav(false)
    const titles = wrapper.findAll('.nav-item').map((el) => el.attributes('data-title'))
    expect(titles).not.toContain('Ausleihe')
    expect(titles).not.toContain('Geräte')
  })
})
