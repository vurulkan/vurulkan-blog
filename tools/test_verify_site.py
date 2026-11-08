"""Regression tests for the Pages artifact gate, independent of Jekyll/Ruby."""

from pathlib import Path
import tempfile
import unittest

from verify_site import verify


class PagesArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)
        self.site = self.source / "_site"
        (self.source / "_posts").mkdir()
        (self.source / "_posts/2026-11-08-ha-cluster.md").write_text("---\ntitle: HA cluster\n---\n")
        self.write("CNAME", "blog.vurulkan.com\n")
        self.write("assets/style.css", "body { color: black; }")
        self.write("assets/theme.js", "console.log('theme');")
        self.write("index.html", self.html("/", '<a href="/posts/ha-cluster/">HA cluster</a>'))
        self.write("posts/ha-cluster/index.html", self.html("/posts/ha-cluster/", "<pre><code>{{ machine }}</code></pre>"))
        self.write("sitemap.xml", '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                   '<url><loc>https://blog.vurulkan.com/posts/ha-cluster/</loc></url></urlset>')

    def write(self, path, text):
        destination = self.site / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")

    def html(self, url, content=""):
        return ('<!doctype html><html><head><title>Kubernetes HA deployment guide</title>'
                f'<link rel="canonical" href="https://blog.vurulkan.com{url}">'
                '<link rel="stylesheet" href="/assets/style.css">'
                '<script src="/assets/theme.js"></script></head><body>'
                '<h1>Kubernetes HA deployment guide</h1><p>Prepare control-plane and worker nodes, '
                'configure the load balancer, and deploy Calico before joining the remaining nodes. '
                'Check network connectivity and component versions before running Ansible, '
                f'then verify node readiness and workload health.</p>{content}</body></html>')

    def test_rendered_artifact_allows_literal_ansible_code(self):
        self.assertEqual([], verify(self.site, self.source))

    def test_source_artifact_cannot_be_published(self):
        self.write("index.html", "---\nlayout: home\n---\n")
        self.write("sitemap.xml", "---\nlayout: null\n---\n{% for post in site.posts %}")
        self.write("_config.yml", "url: https://blog.vurulkan.com")
        errors = verify(self.site, self.source)
        self.assertIn("Source leaked into artifact: _config.yml", errors)
        self.assertIn("Unprocessed front matter: /", errors)
        self.assertTrue(any(error.startswith("Invalid sitemap:") for error in errors), errors)

    def test_missing_generated_post_blocks_deployment(self):
        (self.site / "posts/ha-cluster/index.html").unlink()
        self.assertIn("Missing generated page: /posts/ha-cluster/", verify(self.site, self.source))

    def test_missing_asset_blocks_deployment(self):
        (self.site / "assets/theme.js").unlink()
        self.assertIn("Missing local asset on /: /assets/theme.js", verify(self.site, self.source))

    def test_missing_sitemap_post_blocks_deployment(self):
        self.write("sitemap.xml", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                   '<url><loc>https://blog.vurulkan.com/</loc></url></urlset>')
        self.assertIn("Post missing from sitemap: /posts/ha-cluster/", verify(self.site, self.source))

    def test_wrong_canonical_blocks_deployment(self):
        self.write("posts/ha-cluster/index.html", self.html("/wrong-address/"))
        self.assertTrue(any(error.startswith("Wrong canonical on /posts/ha-cluster/:")
                            for error in verify(self.site, self.source)))


if __name__ == "__main__":
    unittest.main()
