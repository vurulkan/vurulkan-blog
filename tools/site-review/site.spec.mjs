import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const out = path.resolve(import.meta.dirname, '../../review-output');
const article = '/posts/ansible-k8s-ha-cluster-ubuntu/';
const primary = [['home', '/'], ['article', article], ['topic', '/categories/kubernetes/']];
await fs.mkdir(path.join(out, 'screenshots'), { recursive: true });

for (const theme of ['light', 'dark']) {
  for (const width of [375, 390, 768, 1024, 1440]) {
    test(`responsive_${theme}_${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' });
      for (const [name, url] of primary) {
        const response = await page.goto(url);
        expect(response.status()).toBe(200);
        await page.evaluate(() => document.fonts.ready);
        await expect(page.locator('h1')).toHaveCount(1);
        if (name === 'article') await expect(page.locator('.content h2 a.anchor').first()).toHaveAttribute('aria-label', /Link to /);
        if (name === 'topic') {
          const intro = await page.locator('.topic-description').textContent();
          expect((await page.locator('meta[name="description"]').getAttribute('content')).trim()).toBe(intro.trim());
        }
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${name} overflow`).toBe(true);
        if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(out, 'screenshots', `${name}-${theme}-${width}.png`) });
        if ([375, 1440].includes(width)) {
          const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
          await fs.writeFile(path.join(out, `axe-${name}-${theme}-${width}.json`), JSON.stringify(result.violations, null, 2));
          expect(result.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target) })), `${name} accessibility`).toEqual([]);
        }
      }
    });
  }
}

test('secondary_pages_keep_navigation_and_one_heading', async ({ page }) => {
  for (const theme of ['light', 'dark']) {
    await page.emulateMedia({ colorScheme: theme });
    for (const width of [390, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const url of ['/categories/', '/tags/', '/archives/', '/about/', '/not-a-real-page/']) {
        const response = await page.goto(url);
        expect(response.status()).toBe(url.includes('not-a-real') ? 404 : 200);
        await expect(page.locator('h1')).toHaveCount(1);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), url).toBe(true);
      }
    }
  }
});

test('theme_choice_persists_and_system_mode_tracks_os', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.goto('/');
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(5, 6, 10)');
  await page.locator('#mode-toggle').click();
  await page.locator('button[data-theme-mode="light"]').click();
  await page.reload();
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(248, 250, 249)');
  await page.locator('#mode-toggle').click();
  await page.locator('button[data-theme-mode="system"]').click();
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(5, 6, 10)');
  await page.emulateMedia({ colorScheme: 'light' });
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(248, 250, 249)');
});

test('search_finds_articles_and_handles_empty_results', async ({ page }) => {
  await page.goto('/');
  await page.locator('#search-input').fill('debian');
  await expect(page.locator('#search-results a').filter({ hasText: /Debian/ }).first()).toBeVisible();
  await page.locator('#search-input').fill('no-matching-field-note-xyz');
  await expect(page.locator('#search-results')).toContainText(/no results/i);
  await page.locator('#search-input').fill('debian');
  await page.locator('#search-results a').filter({ hasText: /Debian/ }).first().click();
  await expect(page).toHaveURL(/posts\/ansible-k8s-ha-cluster-debian\//);
});

test('heading_links_have_names_and_visible_keyboard_focus', async ({ page }) => {
  await page.goto(article);
  const link = page.locator('.content h2 a.anchor').first();
  await expect(link).toHaveAttribute('aria-label', /Link to /);
  await page.keyboard.press('Tab');
  await link.focus();
  await expect(link).toBeFocused();
  await expect(link).toHaveCSS('opacity', '1');
});

test('mobile_navigation_and_code_copy_work', async ({ page, context }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/');
  await page.locator('#sidebar-trigger').click();
  await page.locator('#sidebar a.nav-link[href="/categories/"]').click();
  await expect(page).toHaveURL(/\/categories\//);
  await page.goto(article);
  await page.locator('.code-header button').first().click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('10.42.0.11');
});

test('keyboard_skip_link_and_mobile_toc_work', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.locator('.skip-link')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(article);
  await page.locator('article > .content').scrollIntoViewIfNeeded();
  await page.locator('button.toc-trigger:visible').first().click();
  await expect(page.locator('#toc-popup')).toBeVisible();
  await expect(page.locator('#toc-popup-content a').first()).toBeVisible();
  await page.locator('#toc-popup-close').click();
  await expect(page.locator('#toc-popup')).not.toBeVisible();
});

test('article_remains_readable_without_javascript_and_at_200_percent', async ({ browser, page }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 844 }, colorScheme: 'dark' });
  const nojs = await context.newPage();
  await nojs.goto(article);
  await expect(nojs.locator('article > .content')).toContainText('HAProxy');
  await expect(nojs.locator('.content a[href*="github.com"]').first()).toBeVisible();
  expect(await nojs.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await context.close();
  await page.goto(article);
  await page.addStyleTag({ content: 'html { font-size: 200% !important; }' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: path.join(out, 'screenshots', 'article-200-percent.png') });
});

test('social_preview_exports_at_1200_by_630', async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 630 });
  await page.goto('/__social-preview/');
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(out, 'social-preview.png') });
});

test('pwa_updates_an_existing_session_and_a_fresh_session', async ({ browser }) => {
  const config = path.resolve(import.meta.dirname, '../../_site/assets/js/data/swconf.js');
  const original = await fs.readFile(config, 'utf8');
  const oldCache = 'review-old-cache';
  const newCache = 'review-new-cache';
  const normal = await browser.newContext({ serviceWorkers: 'allow' });
  let fresh;
  try {
    await fs.writeFile(config, original.replace(/cacheName:\s*'[^']+'/, `cacheName: '${oldCache}'`));
    const page = await normal.newPage();
    await page.goto('http://127.0.0.1:4173/');
    await page.evaluate(() => navigator.serviceWorker.ready);
    await page.reload();
    await page.waitForFunction(() => navigator.serviceWorker.controller);
    await page.evaluate(() => caches.open('review-stale-data').then(cache => cache.put('/stale-test-marker', new Response('old'))));
    await fs.writeFile(config, original.replace(/cacheName:\s*'[^']+'/, `cacheName: '${newCache}'`));
    await page.evaluate(async () => (await navigator.serviceWorker.getRegistration()).update());
    await page.waitForFunction(async () => Boolean((await navigator.serviceWorker.getRegistration())?.waiting));
    await Promise.all([
      page.waitForEvent('load'),
      page.locator('#notification [aria-label="Update"]').click()
    ]);
    await expect.poll(async () => {
      const keys = await page.evaluate(() => caches.keys());
      return { current: keys.includes(newCache), old: keys.includes(oldCache), stale: keys.includes('review-stale-data') };
    }).toEqual({ current: true, old: false, stale: false });
    await expect(page.locator('#field-title')).toBeVisible();
    fresh = await browser.newContext({ serviceWorkers: 'allow' });
    const freshPage = await fresh.newPage();
    await freshPage.goto('http://127.0.0.1:4173/');
    await freshPage.evaluate(() => navigator.serviceWorker.ready);
    await expect(freshPage.locator('#field-title')).toBeVisible();
    await expect.poll(() => freshPage.evaluate(() => caches.keys())).toContain(newCache);
  } finally {
    await fs.writeFile(config, original);
    await normal.close();
    if (fresh) await fresh.close();
  }
});
