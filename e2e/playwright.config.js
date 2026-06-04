import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'cloud',
      testMatch: 'cloud-smoke.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.CLOUD_BASE_URL || 'http://localhost:5173',
      },
    },
    {
      name: 'pi',
      testMatch: 'pi-smoke.spec.js',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: process.env.PI_BASE_URL || 'http://localhost:5174',
      },
    },
  ],
})
