import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { VDateInput } from 'vuetify/labs/VDateInput'
import DateFnsAdapter from '@date-io/date-fns'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'
import { router } from './router/index'

const vuetify = createVuetify({
  components: { ...components, VDateInput },
  directives,
  date: {
    adapter: DateFnsAdapter,
  },
  theme: {
    defaultTheme: 'light',
  },
  defaults: {
    VBtn: { variant: 'outlined' },
    VTextField: { variant: 'outlined', density: 'compact' },
    VSelect: { variant: 'outlined', density: 'compact' },
    VTextarea: { variant: 'outlined', density: 'compact' },
    VAutocomplete: { variant: 'outlined', density: 'compact' },
    VCombobox: { variant: 'outlined', density: 'compact' },
    VFileInput: { variant: 'outlined', density: 'compact' },
    VNumberInput: { variant: 'outlined', density: 'compact' },
    VCheckbox: { variant: 'outlined', density: 'compact' },
    VSwitch: { color: 'success', density: 'compact' },
    VDateInput: { variant: 'outlined', density: 'compact' },
  },
})

createApp(App).use(vuetify).use(router).mount('#app')
