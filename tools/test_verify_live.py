"""Offline regressions for the public deployment check."""
import json
from pathlib import Path
import tempfile
import unittest
from verify_live import SITE_URL, verify


class LiveDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)
        (self.source / "_posts").mkdir()
        (self.source / "_posts/2026-11-09-ha.md").write_text("---\ntitle: HA\n---\n")
        self.post = SITE_URL + "/posts/ha/"
        self.urls = [SITE_URL + "/", self.post]
        self.asset = SITE_URL + "/assets/site.css"
        self.responses = {
            SITE_URL + "/robots.txt": (200, SITE_URL + "/robots.txt", {}, b"User-agent: *\nAllow: /\nSitemap: https://blog.vurulkan.com/sitemap.xml\n"),
            self.asset: (200, self.asset, {"Content-Type": "text/css"}, b"body{}"),
        }
        for url in self.urls:
            schema = json.dumps({"@type": "BlogPosting", "url": url})
            html = f'<!doctype html><html><head><title>HA</title><link rel="canonical" href="{url}"><link rel="stylesheet" href="/assets/site.css"></head><body><h1>HA</h1><pre><code>{{{{ machine }}}}</code></pre><script type="application/ld+json">{schema}</script></body></html>'
            self.responses[url] = (200, url, {}, html.encode())

    def run_check(self):
        xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{url}</loc></url>' for url in self.urls) + '</urlset>'
        self.responses[SITE_URL + "/sitemap.xml"] = (200, SITE_URL + "/sitemap.xml", {}, xml.encode())
        self.requests = []
        def request(url):
            self.requests.append(url)
            return self.responses[url]
        return verify(self.source, request)

    def test_rendered_pages_with_literal_code_and_shared_asset_pass(self):
        result = self.run_check()
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["pages"]), 2)
        self.assertEqual(result["assets"], [self.asset])
        self.assertEqual(self.requests.count(self.asset), 1)

    def test_missing_source_post_and_duplicate_sitemap_are_rejected(self):
        self.urls = [SITE_URL + "/", SITE_URL + "/"]
        errors = self.run_check()["errors"]
        self.assertIn("Missing sitemap URL: " + self.post, errors)
        self.assertIn("Duplicate sitemap URLs", errors)

    def test_canonical_drift_noindex_and_failed_asset_are_rejected(self):
        status, url, _, body = self.responses[self.post]
        self.responses[self.post] = (status, url, {"X-Robots-Tag": "noindex"}, body.replace(f'href="{url}"'.encode(), b'href="https://blog.vurulkan.com/"'))
        self.responses[self.asset] = (404, self.asset, {"Content-Type": "text/html"}, b"Not found")
        errors = self.run_check()["errors"]
        self.assertIn("Canonical mismatch: " + self.post, errors)
        self.assertIn("Unexpected noindex: " + self.post, errors)
        self.assertIn("Asset returned HTML: " + self.asset, errors)
        self.assertTrue(any("expected direct HTTP 200; got 404" in error for error in errors))

    def test_foreign_sitemap_target_is_never_requested(self):
        self.urls.append("https://example.com/private")
        errors = self.run_check()["errors"]
        self.assertIn("Noncanonical sitemap URL: https://example.com/private", errors)
        self.assertNotIn("https://example.com/private", self.requests)

    def test_query_and_fragment_sitemap_targets_are_never_requested(self):
        self.urls.extend([self.post + "?copy=1", self.post + "#section"])
        errors = self.run_check()["errors"]
        for url in self.urls[-2:]:
            self.assertIn("Noncanonical sitemap URL: " + url, errors)
            self.assertNotIn(url, self.requests)

    def test_unavailable_sitemap_is_reported_as_failure(self):
        def unavailable(url):
            raise OSError("Connection unavailable")
        report = verify(self.source, unavailable)
        self.assertEqual(report["pages"], [])
        self.assertTrue(any("Invalid live sitemap" in error for error in report["errors"]))
        self.assertTrue(any("Connection unavailable" in error for error in report["errors"]))

    def test_meta_none_and_duplicate_article_schema_are_rejected(self):
        status, url, headers, body = self.responses[self.post]
        duplicate = '<meta name="robots" content="none"><script type="application/ld+json">' + json.dumps({"@type": "BlogPosting", "url": url}) + '</script>'
        self.responses[self.post] = (status, url, headers, body.replace(b'</head>', duplicate.encode() + b'</head>'))
        errors = self.run_check()["errors"]
        self.assertIn("Unexpected noindex: " + self.post, errors)
        self.assertIn("Article schema mismatch: " + self.post, errors)

    def test_robots_block_and_unrendered_template_are_rejected(self):
        r = SITE_URL + "/robots.txt"
        self.responses[r] = (200, r, {}, b"User-agent: *\nDisallow: /posts/\nSitemap: https://blog.vurulkan.com/sitemap.xml\n")
        status, url, headers, body = self.responses[self.post]
        self.responses[self.post] = (status, url, headers, body.replace(b"<h1>HA</h1>", b"<h1>{{ page.title }}</h1>"))
        errors = self.run_check()["errors"]
        self.assertIn("robots.txt blocks " + self.post, errors)
        self.assertIn("Unrendered or invalid HTML: " + self.post, errors)


if __name__ == "__main__":
    unittest.main()
