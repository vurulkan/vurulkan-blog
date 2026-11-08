#!/usr/bin/env python3
"""Reject unbuilt or incomplete Pages artifacts before they can be deployed."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET


SITE_URL = "https://blog.vurulkan.com"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.title = []
        self.canonical = []
        self.links = []
        self.assets = []
        self.text = []
        self.in_title = False
        self.literal_depth = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag in ("pre", "code", "script", "style"):
            self.literal_depth += 1
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "link":
            rel = attrs.get("rel", "").split()
            if "canonical" in rel:
                self.canonical.append(attrs.get("href", ""))
            if "stylesheet" in rel:
                self.assets.append(attrs.get("href", ""))
        if tag in ("script", "img") and attrs.get("src"):
            self.assets.append(attrs["src"])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in ("pre", "code", "script", "style"):
            self.literal_depth = max(0, self.literal_depth - 1)

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if not self.literal_depth:
            self.text.append(data)


def output_path(site, url):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != "https" or parsed.netloc != "blog.vurulkan.com":
            raise ValueError(f"Unexpected URL origin: {url}")
    path = unquote(parsed.path).lstrip("/")
    result = (site / path).resolve()
    if not result.is_relative_to(site.resolve()):
        raise ValueError(f"URL escapes the artifact: {url}")
    if not path or parsed.path.endswith("/"):
        result /= "index.html"
    return result


def verify(site, source):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    for forbidden in ("_config.yml", "Gemfile", ".github", "_posts", "tools"):
        check(not (site / forbidden).exists(), f"Source leaked into artifact: {forbidden}")
    check((site / "CNAME").is_file() and (site / "CNAME").read_text().strip() == "blog.vurulkan.com",
          "CNAME must preserve blog.vurulkan.com")

    posts = sorted((source / "_posts").glob("*.md"))
    check(bool(posts), "No source posts found")
    expected = ["/posts/" + post.stem[11:] + "/" for post in posts]
    pages = {}
    for url in ["/"] + expected:
        path = output_path(site, url)
        if not path.is_file():
            errors.append(f"Missing generated page: {url}")
            continue
        html = path.read_text(encoding="utf-8")
        page = Page(html)
        pages[url] = page
        check(bool("".join(page.title).strip()), f"Missing HTML title: {url}")
        check(page.canonical == [SITE_URL + url], f"Wrong canonical on {url}: {page.canonical}")
        text = " ".join(page.text)
        check(len(text.strip()) > 200, f"Empty or unbuilt page: {url}")
        check(not html.lstrip().startswith("---"), f"Unprocessed front matter: {url}")
        check(not re.search(r"\{%|\{\{", text), f"Unprocessed Liquid outside code: {url}")
        for asset in page.assets:
            parsed = urlsplit(asset)
            if parsed.scheme or parsed.netloc:
                if parsed.netloc != "blog.vurulkan.com":
                    continue
            check(output_path(site, urljoin(SITE_URL + url, asset)).is_file(),
                  f"Missing local asset on {url}: {asset}")

    if "/" in pages:
        home_links = {urlsplit(url).path for url in pages["/"].links}
        for listing in site.glob("page*/index.html"):
            home_links.update(urlsplit(url).path for url in Page(listing.read_text(encoding="utf-8")).links)
        for url in expected:
            check(url in home_links, f"Post missing from home listings: {url}")

    try:
        xml = (site / "sitemap.xml").read_text(encoding="utf-8")
        sitemap = ET.fromstring(xml)
        check(sitemap.tag == SITEMAP_NS + "urlset", "Sitemap must be a URL set")
        urls = [loc.text for loc in sitemap.iter(SITEMAP_NS + "loc")]
        check(bool(urls), "Sitemap is empty")
        for url in urls:
            check(bool(url) and output_path(site, url).is_file(), f"Missing sitemap target: {url}")
        for url in expected:
            check(SITE_URL + url in urls, f"Post missing from sitemap: {url}")
    except (OSError, ET.ParseError, ValueError) as error:
        errors.append(f"Invalid sitemap: {error}")

    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    failures = verify(args.site, args.source)
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        raise SystemExit(1)
    print("Pages artifact verified: rendered home, all posts, canonicals, sitemap and local assets.")
