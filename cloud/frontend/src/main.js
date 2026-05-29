import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import 'primeicons/primeicons.css'
import App from './App.vue'
import { router } from './router/index'

function dataTableBodyCellPassThrough({ column } = {}) {
  const header = column?.props?.header
  return header ? { 'data-mobile-label': header } : {}
}

createApp(App)
  .use(PrimeVue, {
    theme: {
      preset: Aura,
    },
    pt: {
      datatable: {
        column: {
          bodyCell: dataTableBodyCellPassThrough,
        },
      },
    },
  })
  .use(router)
  .mount('#app')
