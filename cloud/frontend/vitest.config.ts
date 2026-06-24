import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(rootDir, 'src'),
      '@vendiqo/frontend-shared': path.resolve(rootDir, '../../packages/frontend-shared/src'),
    },
  },
  test: {
    environment: 'happy-dom',
    setupFiles: ['tests/setup.ts'],
    include: ['src/**/*.{test,spec}.ts', 'tests/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      include: [
        'src/utils/formRules.ts',
        'src/utils/dashboardMetrics.ts',
        'src/utils/helpArticles.ts',
        'src/utils/orgScope.ts',
        'src/utils/applianceType.ts',
        'src/composables/useAuthSession.ts',
        'src/composables/useCountries.ts',
        'src/composables/usePaymentTypes.ts',
        'src/composables/useTaxCodes.ts',
        'src/composables/useAccountingAccounts.ts',
      ],
      thresholds: { lines: 50, functions: 50, branches: 50, statements: 50 },
    },
  },
})
