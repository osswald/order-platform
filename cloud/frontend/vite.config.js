import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { applyAppVersionEnv } from '../../scripts/vite-version-env.mjs'

applyAppVersionEnv()

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: { labs: true } }),
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
})
