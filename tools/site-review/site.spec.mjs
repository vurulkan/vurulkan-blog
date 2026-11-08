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
