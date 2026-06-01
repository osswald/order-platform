import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import DateFnsAdapter from '@date-io/date-fns'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'
import { router } from './router/index'

const vuetify = createVuetify({
  components,
  directives,
  date: {
    adapter: DateFnsAdapter,
  },
  theme: {
    defaultTheme: 'light',
  },
  defaults: {
    VBtn: { variant: 'outlined' },
    VTextField: { variant: 'outlined' },
    VSelect: { variant: 'outlined' },
    VTextarea: { variant: 'outlined' },
    VAutocomplete: { variant: 'outlined' },
    VCombobox: { variant: 'outlined' },
    VFileInput: { variant: 'outlined' },
    VNumberInput: { variant: 'outlined' },
    VCheckbox: { variant: 'outlined' },
    VSwitch: { variant: 'outlined' },
    VDateInput: { variant: 'outlined' },
  },
})

createApp(App).use(vuetify).use(router).mount('#app')
