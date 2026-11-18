import { defineConfig } from '@playwright/test';

const headless = process.env.SMOKE_HEADLESS !== 'false';
const trace = process.env.PLAYWRIGHT_TRACE || 'off';
const screenshot = process.env.PLAYWRIGHT_SCREENSHOT || 'off';
const video = process.env.PLAYWRIGHT_VIDEO || 'off';

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
    // CI may supply a job-local authenticated session from the normal login flow.
    storageState: process.env.SMOKE_STORAGE_STATE || undefined,
    headless,
    trace,
    screenshot,
    video
  },
  projects: [
    {
      name: 'runs0'
    }
  ]
});
