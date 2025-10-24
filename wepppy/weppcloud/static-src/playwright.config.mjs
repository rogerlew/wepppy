import { defineConfig } from '@playwright/test';

const headless = process.env.SMOKE_HEADLESS !== 'false';

export default defineConfig({
  testDir: './tests/smoke',
  timeout: 90_000,
  expect: {
    timeout: 15_000
  },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }]
  ],
  use: {
    baseURL: process.env.SMOKE_BASE_URL || 'http://localhost:8080',
    headless,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  }
});
