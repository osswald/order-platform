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
      '@tests': path.resolve(rootDir, 'tests'),
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
        'src/api/base.ts',
        'src/utils/money.ts',
        'src/utils/bundleHelpers.ts',
        'src/utils/splitPay.ts',
        'src/composables/useSplitPay.ts',
        'src/utils/paymentTypes.ts',
        'src/utils/stripeTerminalAvailability.ts',
        'src/utils/resolvePayment.ts',
        'src/utils/paymentReceiptPrompt.ts',
        'src/utils/dateFormat.ts',
        'src/utils/pickPaymentType.ts',
        'src/store/index.ts',
        'src/router/guards.ts',
      ],
      thresholds: { lines: 70, functions: 70, branches: 70, statements: 70 },
    },
  },
})
