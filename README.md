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

`CNAME` preserves the custom domain in the generated site. The source `.nojekyll` marker does not replace the explicit Jekyll build. Publishing this repository root from a branch would serve raw templates and make generated post URLs return 404.

## Local verification

Use Ruby 3.3 and Bundler. The lockfile is committed; dependency updates should be deliberate.

```bash
bundle install
JEKYLL_ENV=production bundle exec jekyll build --destination _site
python3 -B -m unittest discover -s tools -p 'test_*.py'
python3 tools/verify_site.py _site
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

This site uses [Chirpy](https://github.com/cotes2020/jekyll-theme-chirpy/) under its MIT license. Local overrides live in `_includes` and `assets/css`. Theme redesign is tracked separately from publishing recovery.
