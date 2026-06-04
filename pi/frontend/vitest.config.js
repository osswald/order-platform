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
            'src/store/index.js',
            'src/router/guards.js',
          ],
          thresholds: { lines: 50, functions: 50, branches: 50, statements: 50 },
        },
      },
    }),
  )
})
