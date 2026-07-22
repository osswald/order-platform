import { describe, expect, it, vi } from 'vitest'

vi.mock('vuetify', () => ({
  useDisplay: () => ({ mobile: { value: false } }),
}))

import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import EventStatusStepper from './EventStatusStepper.vue'
import type { SelectOption } from '@/types/ui'

const allStatusOptions: SelectOption<string>[] = [
  { value: 'config', label: 'Konfiguration' },
  { value: 'test', label: 'Testbetrieb' },
  { value: 'prod', label: 'Produktivbetrieb' },
  { value: 'archive', label: 'Archiviert' },
]

function mountStepper(
  modelValue = 'config',
  selectableStatusOptions: SelectOption<string>[] = [
    { value: 'config', label: 'Konfiguration' },
    { value: 'test', label: 'Testbetrieb' },
  ],
  editMode = true,
  persistStatus?: (status: string) => Promise<boolean>,
) {
  return mount(EventStatusStepper, {
    props: {
      modelValue,
      selectableStatusOptions,
      editMode,
      ...(persistStatus ? { persistStatus } : {}),
    },
    global: {
      stubs: {
        'v-stepper': {
          template: '<div class="v-stepper"><slot /></div>',
          props: ['modelValue', 'flat', 'mobile'],
        },
        'v-stepper-header': { template: '<div class="v-stepper-header"><slot /></div>' },
        'v-stepper-item': {
          template:
            '<button type="button" class="v-stepper-item" :data-value="value" :data-icon="icon" :data-complete="complete" :data-color="color" @click="$emit(\'click\')"><slot />{{ title }}</button>',
          props: ['value', 'title', 'color', 'complete', 'editable', 'icon'],
          emits: ['click'],
        },
        'v-divider': { template: '<hr />' },
        'v-dialog': {
          template: '<div v-if="modelValue" class="v-dialog"><slot /></div>',
          props: ['modelValue', 'maxWidth', 'persistent'],
        },
        'v-card': { template: '<div class="v-card"><slot /></div>' },
        'v-card-title': { template: '<div class="v-card-title"><slot /></div>' },
        'v-card-text': { template: '<div class="v-card-text"><slot /></div>' },
        'v-card-actions': { template: '<div class="v-card-actions"><slot /></div>' },
        'v-spacer': { template: '<span />' },
        'v-btn': {
          template:
            '<button type="button" class="v-btn" :disabled="disabled" :data-loading="loading" @click="$emit(\'click\')"><slot /></button>',
          props: ['variant', 'color', 'type', 'action', 'disabled', 'loading'],
          emits: ['click'],
        },
      },
    },
  })
}

describe('EventStatusStepper', () => {
  it('renders all four lifecycle steps with labels', () => {
    const wrapper = mountStepper('config')
    const items = wrapper.findAll('.v-stepper-item')
    expect(items).toHaveLength(4)
    expect(wrapper.text()).toContain('Konfiguration')
    expect(wrapper.text()).toContain('Testbetrieb')
    expect(wrapper.text()).toContain('Produktivbetrieb')
    expect(wrapper.text()).toContain('Archiviert')
  })

  it('marks earlier steps as complete', () => {
    const wrapper = mountStepper('prod')
    const items = wrapper.findAll('.v-stepper-item')
    expect(items[0].attributes('data-complete')).toBe('true')
    expect(items[1].attributes('data-complete')).toBe('true')
    expect(items[2].attributes('data-complete')).toBe('false')
  })

  it('applies status colors to steps', () => {
    const wrapper = mountStepper('test')
    const items = wrapper.findAll('.v-stepper-item')
    expect(items[1].attributes('data-color')).toBe('info')
    expect(items[2].attributes('data-color')).toBe('success')
  })

  it('uses numeric step values and icons instead of status keys in dots', () => {
    const wrapper = mountStepper('test')
    const items = wrapper.findAll('.v-stepper-item')
    expect(items[0].attributes('data-value')).toBe('1')
    expect(items[1].attributes('data-value')).toBe('2')
    expect(items[2].attributes('data-value')).toBe('3')
    expect(items[3].attributes('data-value')).toBe('4')
    expect(items[0].attributes('data-icon')).toBeUndefined()
    expect(items[1].attributes('data-icon')).toBe('mdi-circle')
    expect(items[0].text()).not.toContain('config')
    expect(items[1].text()).not.toContain('test')
  })

  it('opens confirmation dialog when clicking the next allowed step', async () => {
    const wrapper = mountStepper('config', [
      { value: 'config', label: 'Konfiguration' },
      { value: 'test', label: 'Testbetrieb' },
    ])
    const testStep = wrapper.findAll('.v-stepper-item')[1]
    await testStep.trigger('click')
    await nextTick()
    expect(wrapper.find('.v-dialog').exists()).toBe(true)
    expect(wrapper.find('.v-card-text').text()).toContain('Testbetrieb')
  })

  it('emits new status when transition is confirmed', async () => {
    const wrapper = mountStepper('config', [
      { value: 'config', label: 'Konfiguration' },
      { value: 'test', label: 'Testbetrieb' },
    ])
    await wrapper.findAll('.v-stepper-item')[1].trigger('click')
    await nextTick()
    const confirmBtn = wrapper.findAll('.v-btn').find((btn) => btn.text() === 'Fortfahren')
    expect(confirmBtn).toBeDefined()
    await confirmBtn!.trigger('click')
    await nextTick()
    expect(wrapper.emitted('update:modelValue')).toEqual([['test']])
  })

  it('waits for persistStatus and emits only on success', async () => {
    const persistStatus = vi.fn(async () => true)
    const wrapper = mountStepper(
      'config',
      [
        { value: 'config', label: 'Konfiguration' },
        { value: 'test', label: 'Testbetrieb' },
      ],
      true,
      persistStatus,
    )
    await wrapper.findAll('.v-stepper-item')[1].trigger('click')
    await nextTick()
    const confirmBtn = wrapper.findAll('.v-btn').find((btn) => btn.text() === 'Fortfahren')
    await confirmBtn!.trigger('click')
    await nextTick()
    expect(persistStatus).toHaveBeenCalledWith('test')
    expect(wrapper.emitted('update:modelValue')).toEqual([['test']])
  })

  it('does not emit when persistStatus fails', async () => {
    const persistStatus = vi.fn(async () => false)
    const wrapper = mountStepper(
      'config',
      [
        { value: 'config', label: 'Konfiguration' },
        { value: 'test', label: 'Testbetrieb' },
      ],
      true,
      persistStatus,
    )
    await wrapper.findAll('.v-stepper-item')[1].trigger('click')
    await nextTick()
    const confirmBtn = wrapper.findAll('.v-btn').find((btn) => btn.text() === 'Fortfahren')
    await confirmBtn!.trigger('click')
    await nextTick()
    expect(persistStatus).toHaveBeenCalledWith('test')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.find('.v-dialog').exists()).toBe(false)
  })

  it('does not emit when confirmation is cancelled', async () => {
    const wrapper = mountStepper('config', [
      { value: 'config', label: 'Konfiguration' },
      { value: 'test', label: 'Testbetrieb' },
    ])
    await wrapper.findAll('.v-stepper-item')[1].trigger('click')
    await nextTick()
    const cancelBtn = wrapper.findAll('.v-btn').find((btn) => btn.text() === 'Abbrechen')
    await cancelBtn!.trigger('click')
    await nextTick()
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('does not open dialog for non-adjacent selectable steps', async () => {
    const wrapper = mountStepper('config', allStatusOptions)
    await wrapper.findAll('.v-stepper-item')[2].trigger('click')
    await nextTick()
    expect(wrapper.find('.v-dialog').exists()).toBe(false)
  })

  it('does not allow clicks in create mode', async () => {
    const wrapper = mountStepper('config', [{ value: 'config', label: 'Konfiguration' }], false)
    await wrapper.findAll('.v-stepper-item')[1].trigger('click')
    await nextTick()
    expect(wrapper.find('.v-dialog').exists()).toBe(false)
  })
})
