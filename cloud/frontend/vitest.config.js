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
      include: [
        'src/utils/formRules.js',
        'src/utils/dashboardMetrics.js',
        'src/utils/helpArticles.js',
        'src/utils/orgScope.js',
        'src/utils/applianceType.js',
        'src/composables/useAuthSession.js',
        'src/composables/useCountries.js',
        'src/composables/usePaymentTypes.js',
        'src/composables/useTaxCodes.js',
        'src/composables/useAccountingAccounts.js',
      ],
      thresholds: { lines: 50, functions: 50, branches: 50, statements: 50 },
    },
  },
})
