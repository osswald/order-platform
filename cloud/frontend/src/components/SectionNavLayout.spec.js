import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SectionNavLayout from './SectionNavLayout.vue'

const sections = [
  { id: 'a', title: 'Section A', defaultOpen: true },
  { id: 'b', title: 'Section B' },
]

function mountLayout(props = {}) {
  return mount(SectionNavLayout, {
    props: {
      mobile: false,
      sections,
      activeTab: 'a',
      navAriaLabel: 'Test navigation',
      ...props,
    },
    slots: {
      a: '<div data-testid="slot-a">Content A</div>',
      b: '<div data-testid="slot-b">Content B</div>',
    },
    global: {
      stubs: {
        'v-icon': true,
      },
    },
  })
}

describe('SectionNavLayout', () => {
  it('renders nav section titles and only the active slot on desktop', () => {
    const wrapper = mountLayout()

    expect(wrapper.find('nav').text()).toContain('Section A')
    expect(wrapper.find('nav').text()).toContain('Section B')
    expect(wrapper.find('[data-testid="slot-a"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="slot-b"]').exists()).toBe(false)
  })

  it('emits update:activeTab when a nav item is clicked', async () => {
    const wrapper = mountLayout()
    const buttons = wrapper.findAll('.section-nav-item')

    await buttons[1].trigger('click')

    expect(wrapper.emitted('update:activeTab')).toEqual([['b']])
  })

  it('falls back to the first section when activeTab is invalid', () => {
    const wrapper = mountLayout({ activeTab: 'missing' })

    expect(wrapper.find('[data-testid="slot-a"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="slot-b"]').exists()).toBe(false)
  })

  it('lazy-mounts accordion slots on mobile', () => {
    const wrapper = mountLayout({ mobile: true })

    expect(wrapper.find('.section-nav-accordion').exists()).toBe(true)
    expect(wrapper.findAll('details')).toHaveLength(2)
    expect(wrapper.find('[data-testid="slot-a"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="slot-b"]').exists()).toBe(false)
  })

  it('mounts accordion slot when panel is expanded', async () => {
    const wrapper = mountLayout({ mobile: true })
    const panels = wrapper.findAll('details')

    panels[1].element.open = true
    await panels[1].trigger('toggle')

    expect(wrapper.find('[data-testid="slot-b"]').exists()).toBe(true)
  })

  it('opens the default accordion panel when defaultOpen is set', () => {
    const wrapper = mountLayout({ mobile: true })
    const panels = wrapper.findAll('details')

    expect(panels[0].attributes('open')).toBeDefined()
    expect(panels[1].attributes('open')).toBeUndefined()
  })

  it('uses navAriaLabel on the navigation landmark', () => {
    const wrapper = mountLayout({ navAriaLabel: 'Organisations-Konfiguration' })

    expect(wrapper.find('nav').attributes('aria-label')).toBe('Organisations-Konfiguration')
  })
})
