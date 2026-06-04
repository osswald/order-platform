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
      template: '<button type="submit"><slot /></button>',
      props: ['loading', 'color', 'block', 'size'],
    },
    'v-btn': {
      template: '<button type="submit"><slot /></button>',
      props: ['loading', 'color', 'block', 'size'],
    },
  }
}
