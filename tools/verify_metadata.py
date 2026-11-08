#!/usr/bin/env python3
"""Validate the rendered article metadata rather than trusting front matter."""

import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from verify_site import SITE_URL, SITEMAP_NS, output_path


class Metadata(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.meta, self.schemas, self.json_errors, self.times = {}, [], [], []
        self.h1_count, self.title_count = 0, 0
        self.canonicals, self.script = [], None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "title":
            self.title_count += 1
        if tag == "meta":
            for key in {attrs.get("name"), attrs.get("property")} - {None}:
                self.meta.setdefault(key, []).append(attrs.get("content", ""))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if tag == "time" and attrs.get("datetime"):
            self.times.append(attrs["datetime"])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            try:
                self.schemas.append(json.loads("".join(self.script)))
            except json.JSONDecodeError as error:
                self.json_errors.append(str(error))
            self.script = None


def date(value):
    value = re.sub(r"\s+([+-]\d{4})$", r"\1", value)
    value = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", value)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_page(html, canonical, published, modified, site):
    page, errors = Metadata(html), []

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(page.title_count == 1, "Expected one HTML title")
    check(page.h1_count == 1, "Expected one main H1")
    check(page.canonicals == [canonical], "Canonical does not match the article URL")
    descriptions = page.meta.get("description", [])
    check(len(descriptions) == 1 and len(descriptions[0]) >= 40, "Missing or weak article description")
    check(page.meta.get("og:description") == descriptions, "Open Graph description differs")
    check(page.meta.get("og:url") == [canonical], "Open Graph URL differs")
    viewport = " ".join(page.meta.get("viewport", []))
    check("width=device-width" in viewport and "initial-scale=1" in viewport
          and "user-scalable=no" not in viewport and "maximum-scale=1" not in viewport,
          "Viewport must allow zoom")
    for key in ("og:image", "twitter:image"):
        images = page.meta.get(key, [])
        check(len(images) == 1 and images[0].startswith(SITE_URL + "/"), f"Missing social image: {key}")
        if len(images) == 1:
            try:
                check(output_path(site, images[0]).is_file(), f"Social image does not exist: {key}")
            except ValueError:
                errors.append(f"Social image origin differs: {key}")
    check(not page.json_errors, "Invalid JSON-LD")
    articles = [s for s in page.schemas if isinstance(s, dict) and s.get("@type") in ("BlogPosting", "Article")]
    check(len(articles) == 1, "Expected one article schema")
    if len(articles) == 1:
        article = articles[0]
        check(article.get("url") == canonical, "Schema URL differs")
        check(article.get("mainEntityOfPage", {}).get("@id") == canonical, "Schema main entity differs")
        check(article.get("headline") == (page.meta.get("og:title") or [None])[0], "Schema headline differs")
        check(article.get("description") == (descriptions or [None])[0], "Schema description differs")
        author = article.get("author", {})
        check(author.get("@type") == "Person" and bool(author.get("name"))
              and str(author.get("url", "")).startswith("https://"), "Schema author is incomplete")
        if "image" in article:
            check(bool(article["image"]), "Schema image must not be empty")
        try:
            check(date(article["datePublished"]) == date(published), "Publication date differs from source")
            check(date(article["dateModified"]) == date(modified), "Modified date differs from sitemap")
            check(date(article["dateModified"]) >= date(article["datePublished"]), "Modified date precedes publication")
            visible = {date(value) for value in page.times}
            check(date(published) in visible and date(modified) in visible, "Visible dates differ from metadata")
        except (KeyError, ValueError, TypeError):
            errors.append("Missing or invalid article date")
    return errors, page


def audit(site, source):
    sitemap = ET.parse(site / "sitemap.xml").getroot()
    modified = {e.findtext(SITEMAP_NS + "loc"): e.findtext(SITEMAP_NS + "lastmod")
                for e in sitemap.findall(SITEMAP_NS + "url")}
    matrix, errors, seen = [], [], set()
    for post in sorted((source / "_posts").glob("*.md")):
        canonical = SITE_URL + "/posts/" + post.stem[11:] + "/"
        published = re.search(r"^date:\s*(.+)$", post.read_text(encoding="utf-8"), re.M).group(1)
        html = output_path(site, canonical).read_text(encoding="utf-8")
        failures, page = validate_page(html, canonical, published, modified.get(canonical, ""), site)
        description = (page.meta.get("description") or [""])[0]
        if description in seen:
            failures.append("Duplicate description")
        seen.add(description)
        errors.extend(f"{post.name}: {failure}" for failure in failures)
        matrix.append({"source": post.as_posix(), "url": canonical, "description": description,
                       "published": published, "modified": modified.get(canonical),
                       "h1_count": page.h1_count, "schema_count": len(page.schemas), "errors": failures})
    return matrix, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    matrix, errors = audit(args.site, args.source)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"articles": matrix, "errors": errors}, indent=2) + "\n", encoding="utf-8")
    for error in errors:
        print("ERROR:", error)
    if errors:
        raise SystemExit(1)
    print(f"Article metadata verified: {len(matrix)} unique descriptions, single H1/schema, images and matching dates.")
