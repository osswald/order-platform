import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'
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
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@tests': fileURLToPath(new URL('./tests', import.meta.url)),
      '@vendiqo/frontend-shared': path.resolve(__dirname, '../../packages/frontend-shared/src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5174,
    strictPort: true,
  },
}))
