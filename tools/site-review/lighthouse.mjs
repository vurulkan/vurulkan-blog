import { chromium } from '@playwright/test';
import lighthouse from 'lighthouse';
import { launch } from 'chrome-launcher';
import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
const out = path.join(root, 'review-output');
const server = spawn(process.execPath, ['tools/site-review/server.mjs'], { cwd: root, stdio: 'ignore' });
let browser;
try {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await fetch('http://127.0.0.1:4173').then(r => r.ok).catch(() => false)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  browser = await launch({ chromePath: chromium.executablePath(), chromeFlags: ['--headless', '--no-sandbox', '--disable-dev-shm-usage'] });
  const results = [];
  for (const [name, route] of [['home', '/'], ['article', '/posts/ansible-k8s-ha-cluster-ubuntu/']]) {
    const { lhr, report } = await lighthouse('http://127.0.0.1:4173' + route, { port: browser.port, output: ['html', 'json'], onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'], logLevel: 'error' });
    await fs.writeFile(path.join(out, `lighthouse-${name}.html`), report[0]);
    await fs.writeFile(path.join(out, `lighthouse-${name}.json`), report[1]);
    results.push({ page: name, environment: lhr.environment, scores: Object.fromEntries(Object.entries(lhr.categories).map(([key, category]) => [key, category.score])), lcp: lhr.audits['largest-contentful-paint'].numericValue, cls: lhr.audits['cumulative-layout-shift'].numericValue, tbt: lhr.audits['total-blocking-time'].numericValue });
  }
  await fs.writeFile(path.join(out, 'lighthouse-summary.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
} finally {
  if (browser) await browser.kill();
  server.kill();
}
