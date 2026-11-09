# Vurulkan Blog

Personal Jekyll / Chirpy blog at **https://blog.vurulkan.com/**.

## Publishing

GitHub Pages must use **Settings > Pages > Build and deployment > Source: GitHub Actions**.
Keep **Custom domain: blog.vurulkan.com** and HTTPS enforcement enabled.
Do not select a source branch: this repository contains Jekyll source, not a prebuilt website.

The `Build and Deploy` workflow is the single publishing path:

1. Check out the full history (the last-modified hook uses Git history).
2. Install Ruby 3.3 and the dependencies in `Gemfile.lock`.
3. Build production HTML into `_site`, with an empty base URL for the custom domain.
4. Run the artifact-gate regression tests, verify rendered pages, sitemap, canonical URLs and local assets, then run HTML-Proofer.
5. Upload only `_site` and deploy that artifact to GitHub Pages.
6. Check the public sitemap, source post inventory, canonical URLs, robots directives, article schema and local page assets; upload `live-verification` evidence. The live check retries briefly for Pages propagation and fails visibly if the public site is incomplete.

`CNAME` preserves the custom domain in the generated site. The source `.nojekyll` marker does not replace the explicit Jekyll build. Publishing this repository root from a branch would serve raw templates and make generated post URLs return 404.

## Local verification

Use Ruby 3.3 and Bundler. The lockfile is committed; dependency updates should be deliberate.

```bash
bundle install
JEKYLL_ENV=production bundle exec jekyll build --destination _site
python3 -B -m unittest discover -s tools -p 'test_*.py'
python3 tools/verify_site.py _site
python3 tools/verify_metadata.py _site --report review-output/metadata.json
python3 tools/verify_live.py --report review-output/live.json
bundle exec htmlproofer _site --disable-external
```

The artifact gate checks the current published-post convention, `_posts/YYYY-MM-DD-slug.md` -> `/posts/slug/`, including links across paginated home listings. If drafts, future-dated posts or explicit post permalinks are introduced, update the gate's expected URL inventory alongside that change.

## URLs and crawling

Canonical posts remain at `/posts/slug/` on `https://blog.vurulkan.com`.
The old date-based routes intentionally have no compatibility redirects.

`sitemap.xml` is the single sitemap template. It includes published canonical posts, the home page and explicitly opted-in information pages (`sitemap: true`, currently About). Category/tag navigation stays crawlable even though it is not included in the sitemap. Sitemap omission is not a `noindex` directive.

Post `lastmod` uses `last_modified_at` when available, otherwise the publication date. The existing Git hook supplies modification metadata for edited posts; rebuilding the website does not stamp every post with the deployment time.

`assets/robots.txt` overrides the theme file at the same source path and renders at `/robots.txt`. It allows public crawling and advertises the canonical sitemap. Do not create a second root robots source: it would conflict with the theme asset's permalink. The theme's `jekyll-sitemap` dependency skips both files because explicit sources already exist.

The artifact gate also rejects duplicate, noncanonical, redirect and `noindex` sitemap entries, malformed modification dates and robots rules that block posts or required assets.

## Writing

Add Markdown files under `_posts` with title, date (including timezone), description, categories and tags. Keep existing slugs stable when editing a post. For Ansible/Jinja examples, protect literal Liquid-like syntax with Liquid `raw` / `endraw` tags so Jekyll does not evaluate it.

Source-based guides link to the README commit used for the update. Review those repositories for newer deployment instructions before using the examples.

Planning and milestone receipts: [vurulkan/milestones/vurulkan-blog](https://github.com/vurulkan/milestones/tree/main/vurulkan-blog).

## Theme

This site uses [Chirpy](https://github.com/cotes2020/jekyll-theme-chirpy/) under its MIT license. The approved field-notes design follows the colors at vurulkan.com, with system/light/dark theme choices, local Space Grotesk / IBM Plex Sans / Fira Code fonts, and the existing Chirpy search and TOC.

Article JSON-LD comes from `jekyll-seo-tag` only. Descriptions, publication/update timestamps, social images and rendered heading counts are checked before publishing. Keep publication dates stable, and update `last_modified_at` only for real article edits.

The upstream-derived files below are based on Chirpy 7.6.0 and should be diffed against the theme gem during upgrades:

- `_includes/head.html`: zoom-friendly viewport, local font stylesheet, branding colors and escaped PWA query string.
- `_includes/sidebar.html`: descriptive avatar and navigation semantics.
- `_includes/datetime.html`: machine-readable `datetime` attributes alongside the theme's timestamp handling.
- `_includes/post-nav.html`: accessible names include the visible article titles.
- `_layouts/default.html`: skip link, main target and named back-to-top control.
- `_layouts/home.html`: home introduction and H2 article cards; upstream pagination remains intact.
- `_layouts/category.html`: topic descriptions and readable article summaries.

Brand tokens and responsive refinements live in `assets/css/jekyll-theme-chirpy.scss`; the small `assets/js/site.js` adds control labels and keyboard focus for scrollable code/tables. Font license text is included under `assets/fonts`. The code-generated social image can be reproduced from `tools/site-review/social-preview.html`.

## Isolated visual review

The **Site Review** workflow builds the site and runs Playwright/axe in an isolated CI Chromium browser. It does not control an existing desktop browser or use personal browser profiles. It checks five viewport widths in light/dark modes, search, theme persistence, mobile TOC, keyboard navigation, no-JavaScript reading and 200% text sizing. Screenshots, accessibility findings, metadata and Lighthouse lab reports are downloadable from the workflow artifact.

To run the same review in a development environment after a production build:

```bash
npm ci --prefix tools/site-review
npx --prefix tools/site-review playwright install --with-deps chromium
npm test --prefix tools/site-review
node tools/site-review/lighthouse.mjs
```

Lighthouse is a laboratory measurement. It does not establish field Core Web Vitals or a Google ranking result. Run Site Review before publishing layout or theme changes.
