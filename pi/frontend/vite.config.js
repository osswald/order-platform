import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { applyAppVersionEnv } from '../../scripts/vite-version-env.mjs'

applyAppVersionEnv()

export default defineConfig(({ mode }) => ({
  base: mode === 'android' ? './' : '/',
  define: mode === 'android'
    ? { 'import.meta.env.VITE_ANDROID_APP': JSON.stringify('true') }
    : {},
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    // Use a different port than cloud/frontend (5173) so both can run locally.
    port: 5174,
    strictPort: true,
  },
}))
