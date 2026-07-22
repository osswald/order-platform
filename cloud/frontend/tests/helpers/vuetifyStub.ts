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
      template:
        '<button type="button" :data-color="color" :data-variant="variant" :data-icon="icon" v-bind="$attrs"><slot /></button>',
      props: ['loading', 'color', 'block', 'size', 'variant', 'icon'],
    },
    'v-btn': {
      template:
        '<button type="button" :data-color="color" :data-variant="variant" :data-icon="icon" v-bind="$attrs"><slot /></button>',
      props: ['loading', 'color', 'block', 'size', 'variant', 'icon'],
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
