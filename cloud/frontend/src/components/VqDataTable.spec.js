import { describe, expect, it } from 'vitest'
import { defineComponent, ref } from 'vue'
import { mount } from '@vue/test-utils'
import VqDataTable from './VqDataTable.vue'

const headers = [{ title: 'ID', key: 'id' }]
const items = Array.from({ length: 11 }, (_, index) => ({ id: index + 1 }))

function mountWithCapturedTableProps(props) {
  const captured = ref(null)
  const DataTableStub = defineComponent({
    inheritAttrs: false,
    props: ['items', 'itemsPerPage', 'mobileBreakpoint'],
    setup(tableProps) {
      captured.value = tableProps
      return () => null
    },
  })

  const wrapper = mount(VqDataTable, {
    props,
    global: {
      stubs: {
        'v-data-table': DataTableStub,
      },
    },
  })

  return { wrapper, captured }
}

describe('VqDataTable', () => {
  it('defaults items-per-page to -1 when not provided', () => {
    const { captured } = mountWithCapturedTableProps({ headers, items })
    expect(captured.value.itemsPerPage).toBe(-1)
  })

  it('respects explicit items-per-page', () => {
    const { captured } = mountWithCapturedTableProps({
      headers,
      items,
      itemsPerPage: 20,
    })
    expect(captured.value.itemsPerPage).toBe(20)
  })
})
