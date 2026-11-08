import { defineConfig } from '@playwright/test';
import path from 'node:path';

export default defineConfig({
  testDir: '.',
  testMatch: 'site.spec.mjs',
  timeout: 180000,
  expect: { timeout: 15000 },
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: '../../review-output/playwright.json' }], ['html', { outputFolder: '../../review-output/playwright-report', open: 'never' }]],
  outputDir: '../../review-output/test-results',
  use: { baseURL: 'http://127.0.0.1:4173', viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block', trace: 'retain-on-failure' },
  webServer: { command: 'node tools/site-review/server.mjs', cwd: path.resolve(import.meta.dirname, '../..'), url: 'http://127.0.0.1:4173', reuseExistingServer: false }
});
