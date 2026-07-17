export function vuetifyStubs() {
  return {
    VForm: {
      template: '<form @submit.prevent="$attrs.onSubmit?.($event)"><slot /></form>',
      methods: {
        validate() {
          return Promise.resolve({ valid: true })
        },
      },
    },
    'v-form': {
      template: '<form @submit.prevent="$attrs.onSubmit?.($event)"><slot /></form>',
      methods: {
        validate() {
          return Promise.resolve({ valid: true })
        },
      },
    },
    VTextField: {
      template:
        '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
      props: ['modelValue', 'label', 'type', 'rules'],
    },
    'v-text-field': {
      template:
        '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
      props: ['modelValue', 'label', 'type', 'rules'],
    },
    VBtn: {
      template: '<button type="button" v-bind="$attrs"><slot /></button>',
      props: ['loading', 'color', 'block', 'size', 'variant'],
    },
    'v-btn': {
      template: '<button type="button" v-bind="$attrs"><slot /></button>',
      props: ['loading', 'color', 'block', 'size', 'variant'],
    },
    VDataTable: {
      template: '<div data-testid="v-data-table"><slot /></div>',
      props: ['items', 'itemsPerPage', 'headers', 'mobileBreakpoint'],
    },
    'v-data-table': {
      template: '<div data-testid="v-data-table"><slot /></div>',
      props: ['items', 'itemsPerPage', 'headers', 'mobileBreakpoint'],
    },
  }
}
