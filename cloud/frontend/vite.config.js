import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    // Pi frontend dev server uses 5174 (see pi/frontend) so both can run at once.
    port: 5173,
    strictPort: true,
  },
})
