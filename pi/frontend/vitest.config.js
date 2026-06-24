import { defineConfig, mergeConfig } from 'vitest/config'
import baseViteConfig from './vite.config.js'

export default defineConfig((configEnv) => {
  const viteConfig =
    typeof baseViteConfig === 'function' ? baseViteConfig(configEnv) : baseViteConfig
  return mergeConfig(
    viteConfig,
    defineConfig({
      test: {
        environment: 'happy-dom',
        setupFiles: ['tests/setup.js'],
        include: ['src/**/*.{test,spec}.js', 'tests/**/*.{test,spec}.js'],
        coverage: {
          provider: 'v8',
          include: [
            'src/utils/money.js',
            'src/utils/bundleHelpers.js',
            'src/utils/splitPay.js',
            'src/composables/useSplitPay.js',
            'src/utils/paymentTypes.js',
            'src/utils/stripeTerminalAvailability.js',
            'src/utils/resolvePayment.js',
            'src/store/index.js',
            'src/router/guards.js',
          ],
          thresholds: { lines: 60, functions: 60, branches: 60, statements: 60 },
        },
      },
    }),
  )
})
