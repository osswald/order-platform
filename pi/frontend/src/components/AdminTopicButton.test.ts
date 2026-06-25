import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import AdminTopicButton from './AdminTopicButton.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/admin/sync', name: 'admin-sync', component: { template: '<div/>' } }],
})

describe('AdminTopicButton', () => {
  it('renders label and icon slot', () => {
    const wrapper = mount(AdminTopicButton, {
      props: { label: 'Synchronisation' },
      slots: { icon: '<svg data-testid="icon" />' },
    })
    expect(wrapper.text()).toContain('Synchronisation')
    expect(wrapper.find('[data-testid="icon"]').exists()).toBe(true)
  })

  it('emits click when used as button', async () => {
    const wrapper = mount(AdminTopicButton, {
      props: { label: 'Betrieb' },
    })
    await wrapper.find('.admin-topic-btn').trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('renders RouterLink when to is given', async () => {
    const wrapper = mount(AdminTopicButton, {
      props: { label: 'Sync', to: { name: 'admin-sync' } },
      global: { plugins: [router] },
    })
    await router.isReady()
    const link = wrapper.find('a.admin-topic-btn')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toContain('/admin/sync')
  })
})
