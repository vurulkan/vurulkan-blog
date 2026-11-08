"""Focused regressions for the article SEO output contract."""

import json
from pathlib import Path
import tempfile
import unittest

from verify_metadata import validate_page


class ArticleMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name)
        (self.site / "social.png").write_bytes(b"image fixture")
        self.url = "https://blog.vurulkan.com/posts/ha-cluster/"
        self.published = "2025-11-28T22:00:00+03:00"
        self.modified = "2026-11-09T00:30:00+03:00"
        self.description = "Deploy an HA Kubernetes control plane using Ansible and verify node readiness."
        self.schema = {"@context": "https://schema.org", "@type": "BlogPosting", "url": self.url,
                       "mainEntityOfPage": {"@id": self.url}, "headline": "HA cluster", "description": self.description,
                       "author": {"@type": "Person", "name": "M. Volkan", "url": "https://vurulkan.com/"},
                       "datePublished": self.published, "dateModified": self.modified}

    def html(self):
        return (f'<html><head><title>HA cluster | Field notes</title><link rel="canonical" href="{self.url}">'
                f'<meta name="description" content="{self.description}"><meta property="og:description" content="{self.description}">'
                f'<meta property="og:title" content="HA cluster"><meta property="og:url" content="{self.url}">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<meta property="og:image" content="https://blog.vurulkan.com/social.png">'
                '<meta property="twitter:image" content="https://blog.vurulkan.com/social.png">'
                f'<script type="application/ld+json">{json.dumps(self.schema)}</script></head><body><h1>HA cluster</h1>'
                f'<time datetime="{self.published}">Published</time><time datetime="{self.modified}">Updated</time></body></html>')

    def errors(self, html=None):
        return validate_page(html or self.html(), self.url, self.published, self.modified, self.site)[0]

    def test_consistent_article_metadata_passes(self):
        self.assertEqual([], self.errors())

    def test_combined_twitter_and_open_graph_meta_is_supported(self):
        html = self.html().replace('property="og:description"', 'name="twitter:description" property="og:description"')
        self.assertEqual([], self.errors(html))

    def test_source_date_with_numeric_timezone_is_supported(self):
        errors, _ = validate_page(self.html(), self.url, "2025-11-28 22:00:00 +0300", self.modified, self.site)
        self.assertEqual([], errors)

    def test_duplicate_article_schema_is_rejected(self):
        html = self.html().replace('</head>', f'<script type="application/ld+json">{json.dumps(self.schema)}</script></head>')
        self.assertIn("Expected one article schema", self.errors(html))

    def test_empty_article_image_is_rejected(self):
        self.schema["image"] = ""
        self.assertIn("Schema image must not be empty", self.errors())

    def test_duplicate_main_heading_is_rejected(self):
        self.assertIn("Expected one main H1", self.errors(self.html().replace('</body>', '<h1>Repeated title</h1></body>')))

    def test_zoom_restriction_is_rejected(self):
        self.assertIn("Viewport must allow zoom", self.errors(self.html().replace('initial-scale=1', 'initial-scale=1, user-scalable=no')))

    def test_publication_date_must_match_source(self):
        self.schema["datePublished"] = "2024-11-28T22:00:00+03:00"
        self.assertIn("Publication date differs from source", self.errors())

    def test_modified_date_must_match_sitemap(self):
        self.schema["dateModified"] = "2026-10-01T00:30:00+03:00"
        self.assertIn("Modified date differs from sitemap", self.errors())

    def test_missing_social_image_is_rejected(self):
        (self.site / "social.png").unlink()
        self.assertIn("Social image does not exist: og:image", self.errors())


if __name__ == "__main__":
    unittest.main()
