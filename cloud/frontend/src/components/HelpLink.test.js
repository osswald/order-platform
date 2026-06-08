import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import HelpLink from './HelpLink.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/help/:slug', name: 'help-article', component: { template: '<div />' } },
  ],
})

describe('HelpLink', () => {
  it('renders icon link to the help article route', async () => {
    const wrapper = mount(HelpLink, {
      props: { slug: 'event-setup', variant: 'icon' },
      global: {
        plugins: [router],
        stubs: {
          VBtn: {
            template: '<a :href="to ? `#${to.name}-${to.params.slug}` : undefined"><slot /></a>',
            props: ['to', 'icon', 'variant', 'ariaLabel', 'size'],
          },
        },
      },
    })

    await router.isReady()

    const link = wrapper.find('a')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toBe('#help-article-event-setup')
  })

  it('renders text link for link variant', async () => {
    const wrapper = mount(HelpLink, {
      props: { slug: 'stripe-connect', variant: 'link', label: 'Stripe-Hilfe' },
      global: {
        plugins: [router],
      },
    })

    await router.isReady()

    const link = wrapper.find('a.help-link')
    expect(link.text()).toBe('Stripe-Hilfe')
    expect(link.attributes('href')).toBe('/help/stripe-connect')
  })
})
