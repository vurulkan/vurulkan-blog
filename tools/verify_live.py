#!/usr/bin/env python3
"""Check the public deployment against the checked-out post inventory."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

from verify_site import Page, SITE_URL, SITEMAP_NS
from verify_metadata import Metadata


def local_url(url):
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.netloc == "blog.vurulkan.com"


class LocalRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not local_url(newurl):
            raise ValueError("Redirect outside the canonical origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    if not local_url(url):
        raise ValueError("Only the canonical production origin can be checked")
    opener = urllib.request.build_opener(LocalRedirects())
    request = urllib.request.Request(url, headers={"User-Agent": "Vurulkan-Publication-Check/1.0"})
    with opener.open(request, timeout=30) as response:
        body = response.read(8 * 1024 * 1024 + 1)
        if len(body) > 8 * 1024 * 1024:
            raise ValueError("Response exceeds the 8 MiB check limit")
        return response.status, response.geturl(), dict(response.headers.items()), body


def verify(source, request=fetch):
    report = {"observed_at": datetime.now(timezone.utc).isoformat(), "pages": [], "assets": [], "errors": []}
    errors = report["errors"]

    def get(url):
        try:
            status, final, headers, body = request(url)
            if status != 200 or final != url:
                errors.append(f"{url}: expected direct HTTP 200; got {status} at {final}")
            return {key.lower(): value for key, value in headers.items()}, body
        except (OSError, ValueError) as error:
            errors.append(f"{url}: {error}")
            return {}, b""

    _, robots_body = get(SITE_URL + "/robots.txt")
    robots = robots_body.decode("utf-8", errors="replace")
    report["robots"] = robots
    policy = RobotFileParser()
    policy.parse(robots.splitlines())
    if not re.search(r"(?im)^sitemap:\s*" + re.escape(SITE_URL + "/sitemap.xml") + r"\s*$", robots):
        errors.append("robots.txt must advertise the canonical sitemap")
    _, sitemap = get(SITE_URL + "/sitemap.xml")
    try:
        root = ET.fromstring(sitemap)
        if root.tag != SITEMAP_NS + "urlset":
            raise ValueError("Expected a namespaced sitemap urlset")
        urls = [item.findtext(SITEMAP_NS + "loc", "") for item in root.findall(SITEMAP_NS + "url")]
    except (ET.ParseError, ValueError) as error:
        errors.append(f"Invalid live sitemap: {error}")
        return report
    expected = {SITE_URL + "/posts/" + post.stem[11:] + "/" for post in (source / "_posts").glob("*.md")}
    if not expected:
        errors.append("Source post inventory is empty")
    for url in sorted(expected | {SITE_URL + "/"}):
        if url not in urls:
            errors.append(f"Missing sitemap URL: {url}")
    if len(urls) != len(set(urls)):
        errors.append("Duplicate sitemap URLs")
    assets = set()
    for url in dict.fromkeys(urls):
        if not local_url(url) or urlsplit(url).query or urlsplit(url).fragment:
            errors.append(f"Noncanonical sitemap URL: {url}")
            continue
        if not policy.can_fetch("Googlebot", url) or not policy.can_fetch("*", url):
            errors.append(f"robots.txt blocks {url}")
        headers, body = get(url)
        html = body.decode("utf-8", errors="replace")
        page, metadata = Page(html), Metadata(html)
        if page.canonical != [url]:
            errors.append(f"Canonical mismatch: {url}")
        header_robots = re.split(r"[,;\s]+", headers.get("x-robots-tag", "").lower())
        if {"noindex", "none"}.intersection(page.robots + header_robots):
            errors.append(f"Unexpected noindex: {url}")
        if not html.lstrip().lower().startswith("<!doctype html") or re.search(r"\{%|\{\{|^---", " ".join(page.text)):
            errors.append(f"Unrendered or invalid HTML: {url}")
        if metadata.h1_count != 1 or metadata.title_count != 1 or metadata.json_errors:
            errors.append(f"Invalid headings, title or JSON-LD: {url}")
        if url in expected:
            articles = [s for s in metadata.schemas if isinstance(s, dict) and s.get("@type") in ("Article", "BlogPosting")]
            if len(articles) != 1 or articles[0].get("url") != url:
                errors.append(f"Article schema mismatch: {url}")
        report["pages"].append({"url": url, "canonical": page.canonical, "h1_count": metadata.h1_count})
        for asset in page.assets + metadata.meta.get("og:image", []) + metadata.meta.get("twitter:image", []):
            target = urljoin(url, asset)
            if local_url(target):
                assets.add(target)
    for asset in sorted(assets):
        if not policy.can_fetch("Googlebot", asset):
            errors.append(f"robots.txt blocks required asset: {asset}")
        headers, body = get(asset)
        if not body:
            errors.append(f"Empty asset: {asset}")
        if "text/html" in headers.get("content-type", "").lower():
            errors.append(f"Asset returned HTML: {asset}")
        report["assets"].append(asset)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path, default=Path("review-output/live.json"))
    args = parser.parse_args()
    report = verify(args.source)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Live check: {len(report['pages'])} pages, {len(report['assets'])} assets, {len(report['errors'])} errors")
    for error in report["errors"]:
        print(error)
    return bool(report["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
