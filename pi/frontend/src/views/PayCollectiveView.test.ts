import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import { COLLECTIVE_RETURN_TO_REGISTER } from '@/utils/collectiveReturnNav'

const push = vi.fn()
const routeQuery = ref<Record<string, string>>({ id: '7' })

vi.mock('vue-router', () => ({
  useRoute: () => ({
    get query() {
      return routeQuery.value
    },
  }),
  useRouter: () => ({ push }),
}))

vi.mock('@/api', () => ({
  api: vi.fn(async () => ({ name: 'Personal', line_groups: [] })),
}))

vi.mock('@/composables/useEventContext', () => ({
  useEventContext: () => ({
    event: ref({ id: 1, name: 'Sommerfest', currency: 'CHF' }),
  }),
}))

import PayCollectiveView from './PayCollectiveView.vue'

describe('PayCollectiveView', () => {
  beforeEach(() => {
    push.mockReset()
    routeQuery.value = { id: '7' }
  })

  it('returns to collective-open preserving register return query', async () => {
    routeQuery.value = {
      id: '7',
      returnTo: COLLECTIVE_RETURN_TO_REGISTER,
      registerUuid: 'register-1',
    }
    const wrapper = mount(PayCollectiveView, {
      global: {
        stubs: {
          SplitPaySettleScreen: {
            name: 'SplitPaySettleScreen',
            template: '<button type="button" data-testid="back" @click="$emit(\'back\')">back</button>',
          },
        },
      },
    })
    await flushPromises()
    await wrapper.get('[data-testid="back"]').trigger('click')
    expect(push).toHaveBeenCalledWith({
      name: 'collective-open',
      query: {
        returnTo: COLLECTIVE_RETURN_TO_REGISTER,
        registerUuid: 'register-1',
      },
    })
  })

  it('returns to collective-open without query when entered as waiter', async () => {
    const wrapper = mount(PayCollectiveView, {
      global: {
        stubs: {
          SplitPaySettleScreen: {
            name: 'SplitPaySettleScreen',
            template: '<button type="button" data-testid="back" @click="$emit(\'back\')">back</button>',
          },
        },
      },
    })
    await flushPromises()
    await wrapper.get('[data-testid="back"]').trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'collective-open' })
  })
})
