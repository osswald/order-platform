import { createApp, watch } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { de as vuetifyDe, en as vuetifyEn } from 'vuetify/locale'
import DateFnsAdapter from '@date-io/date-fns'
import { de as dateFnsDe } from 'date-fns/locale/de'
import { enUS as dateFnsEnUS } from 'date-fns/locale/en-US'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import App from './App.vue'
import { router } from './router/index'
import { i18n } from './i18n'
import { resolveInitialTheme } from './utils/themePreference'

const vuetify = createVuetify({
  // VDateInput is included in the v4 core components namespace (no separate labs import).
  components: { ...components },
  directives,
  locale: {
    locale: 'de',
    fallback: 'en',
    messages: { de: vuetifyDe, en: vuetifyEn },
  },
  date: {
    adapter: DateFnsAdapter,
    locale: {
      de: dateFnsDe,
      en: dateFnsEnUS,
    },
  },
  theme: {
    defaultTheme: resolveInitialTheme(),
    themes: {
      light: {},
      dark: {},
    },
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

function syncVuetifyLocale(locale: string) {
  const code = locale === 'en' ? 'en' : 'de'
  vuetify.locale.current.value = code
}

syncVuetifyLocale(i18n.global.locale.value)
watch(i18n.global.locale, (locale) => syncVuetifyLocale(locale))

createApp(App).use(i18n).use(vuetify).use(router).mount('#app')
