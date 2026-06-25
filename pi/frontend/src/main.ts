import { createApp } from 'vue'
import App from './App.vue'
import router from '@/router'
import { isAndroidApp } from '@/api'
import { applyAndroidSafeAreaInsets } from '@/utils/androidInsets'
import '@/styles/app.css'

if (isAndroidApp() && typeof document !== 'undefined') {
  document.documentElement.classList.add('android-app')
  applyAndroidSafeAreaInsets()
  window.addEventListener('resize', applyAndroidSafeAreaInsets)
}

createApp(App).use(router).mount('#app')
