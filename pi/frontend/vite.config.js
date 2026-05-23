import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    // Use a different port than cloud/frontend (5173) so both can run locally.
    port: 5174,
    strictPort: true,
  },
})
