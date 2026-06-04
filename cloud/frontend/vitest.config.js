import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    setupFiles: ['tests/setup.js'],
    include: ['src/**/*.{test,spec}.js', 'tests/**/*.{test,spec}.js'],
    coverage: {
      provider: 'v8',
      include: ['src/utils/formRules.js', 'src/utils/dashboardMetrics.js'],
      thresholds: { lines: 50, functions: 50, branches: 50, statements: 50 },
    },
  },
})
