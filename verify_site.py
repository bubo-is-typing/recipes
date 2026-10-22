#!/usr/bin/env python3
import http.server
import html as html_module
import json
import os
import re
import socketserver
import struct
import threading
import urllib.request
from pathlib import Path

import build

root = Path(__file__).parent
recipes = sorted(p for p in root.glob("*.md") if p.name != "README.md")
expected_recipes = len(recipes)
assert expected_recipes > 0
images = []
for recipe in recipes:
    text = recipe.read_text()
    match = re.search(r"^image:\s*(\S+)", text, re.M)
    if not match:
        continue  # Text-first recipes may await a faithful, licensed photograph.
    image = root / match.group(1)
    assert image.exists(), image
    assert image.suffix == ".png", image
    with image.open("rb") as handle:
        signature = handle.read(24)
    assert signature[:8] == b"\x89PNG\r\n\x1a\n", image
    width, height = struct.unpack(">II", signature[16:24])
    assert (width, height) == (1152, 768), (image, width, height)
    images.append((image.name, image.stat().st_size))

html = sorted((root / "_site").glob("*.html"))
assert len(html) == expected_recipes + 2, len(html)
de_html = sorted((root / "_site" / "de").glob("*.html"))
assert len(de_html) == expected_recipes + 2, len(de_html)
for page in html + de_html:
    content = page.read_text(encoding="utf-8")
    for crawler in ("robots", "googlebot"):
        assert f'<meta name="{crawler}" content="noindex, nofollow, noarchive, nosnippet, noimageindex">' in content, page
for recipe in recipes:
    english_page = (root / "_site" / f"{recipe.stem}.html").read_text(encoding="utf-8")
    german_page = (root / "_site" / "de" / f"{recipe.stem}.html").read_text(encoding="utf-8")
    assert f'href="de/{recipe.stem}.html"' in english_page, recipe
    assert f'href="../{recipe.stem}.html"' in german_page, recipe
    assert '<html lang="de-CH">' in german_page, recipe
    assert 'data-pagefind-body' in german_page, recipe
    assert 'name="robots" content="noindex' in german_page, recipe
stale_svg = list((root / "_site" / "assets" / "images").glob("*.svg"))
assert not stale_svg, stale_svg
pagefind = root / "_site" / "pagefind"
required_pagefind_assets = [
    pagefind / "pagefind.js",
    pagefind / "pagefind-component-ui.js",
    pagefind / "pagefind-component-ui.css",
]
assert all(path.exists() for path in required_pagefind_assets), required_pagefind_assets
pagefind_fragments = list((pagefind / "fragment").glob("*.pf_fragment"))
assert len(pagefind_fragments) == 2 * expected_recipes, len(pagefind_fragments)
assert len(list((pagefind / "fragment").glob("en_*.pf_fragment"))) == expected_recipes
assert len(list((pagefind / "fragment").glob("de-ch_*.pf_fragment"))) == expected_recipes
assert list(pagefind.glob("pagefind.en_*.pf_meta"))
assert list(pagefind.glob("pagefind.de-ch_*.pf_meta"))
if len(images) < expected_recipes:
    assert "Photo coming soon" in (root / "_site" / "index.html").read_text()
site_base_url = os.environ.get("SITE_BASE_URL", "/recipes/").strip().strip("/")
site_base_url = f"/{site_base_url}/" if site_base_url else "/"
origin = os.environ.get("SITE_ORIGIN", "https://recipes.bubo.page" if site_base_url == "/" else "https://bubo-is-typing.github.io").rstrip("/")
assert origin.startswith("https://") and "/" not in origin[8:], origin
social_cards = sorted((root / "_site" / "og").rglob("*.png"))
assert len(social_cards) == 2 * expected_recipes + 2, len(social_cards)
for locale, prefix in (("en", ""), ("de-CH", "de/")):
    for slug in ["index"] + [recipe.stem for recipe in recipes]:
        page = root / "_site" / prefix / f"{slug}.html"
        image = root / "_site" / "og" / prefix / f"{slug}.png"
        assert image.exists(), image
        with image.open("rb") as handle:
            signature = handle.read(24)
        assert signature[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", signature[16:24]) == (1200, 630), image
        content = page.read_text(encoding="utf-8")
        metadata = {key: html_module.unescape(value) for key, value in re.findall(r'<meta (?:property|name)="([^"]+)" content="([^"]*)">', content)}
        canonical_name = f"{slug}{'' if site_base_url == '/' else '.html'}" if slug != "index" else ("" if site_base_url == "/" else "index.html")
        expected_url = f"{origin}{site_base_url}{prefix}{canonical_name}"
        expected_image = f"{origin}{site_base_url}og/{prefix}{slug}.png"
        recipe = build.parse_recipe((root / prefix / f"{slug}.md")) if slug != "index" else None
        title = recipe.title if recipe else build.UI[locale]["all"]
        description = (f"{recipe.title}, {build.UI[locale]['recipe'].lower()} · {build.UI[locale]['by']} {build.creator_label(recipe.creator, locale)}."
                       if recipe else build.UI[locale]["hero_intro"])
        alt = (f"{recipe.title} — {recipe.image_alt}" if recipe.image_alt else recipe.title) if recipe else build.UI[locale]["site"]
        expected = {"og:url": expected_url, "og:image": expected_image, "twitter:image": expected_image,
                    "og:type": "article" if recipe else "website", "og:title": title, "twitter:title": title,
                    "og:description": description, "twitter:description": description,
                    "og:locale": "de_CH" if locale == "de-CH" else "en_US", "og:site_name": build.UI[locale]["site"],
                    "og:image:type": "image/png", "og:image:width": "1200", "og:image:height": "630",
                    "og:image:alt": alt, "twitter:card": "summary_large_image"}
        for key, value in expected.items():
            assert metadata.get(key) == value, (page, key, metadata.get(key), value)
pagefind_bundle_path = f"{site_base_url}pagefind/"
index = (root / "_site" / "index.html").read_text(encoding="utf-8")
expected_pagefind_config = (
    f'<pagefind-config base-url="{site_base_url}" '
    f'bundle-path="{pagefind_bundle_path}"></pagefind-config>'
)
assert expected_pagefind_config in index, expected_pagefind_config
de_index = (root / "_site" / "de" / "index.html").read_text(encoding="utf-8")
assert expected_pagefind_config in de_index, expected_pagefind_config
assert '<html lang="de-CH">' in de_index
assert 'href="../pagefind/pagefind-component-ui.css"' in de_index
assert 'src="../pagefind/pagefind-component-ui.js"' in de_index
headers = (root / "_site" / "_headers").read_text(encoding="utf-8")
expected_headers = """/*
  X-Robots-Tag: noindex, nofollow, noarchive, nosnippet, noimageindex
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
"""
assert headers == expected_headers, headers
assert "Content-Security-Policy" not in headers

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

os.chdir(root / "_site")
server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{server.server_address[1]}"
urls = (
    ["/"]
    + [f"/{recipe.stem}.html" for recipe in recipes]
    + ["/de/", "/de/404.html"]
    + [f"/de/{recipe.stem}.html" for recipe in recipes]
    + [f"/assets/images/{name}" for name, _ in images]
    + [f"/og/{path.relative_to(root / '_site' / 'og').as_posix()}" for path in social_cards]
    + ["/assets/style.css", "/assets/site.js"]
    + [f"/pagefind/{path.name}" for path in required_pagefind_assets]
    + [f"/pagefind/fragment/{path.name}" for path in pagefind_fragments]
)
try:
    for url in urls:
        with urllib.request.urlopen(base + url, timeout=10) as response:
            assert response.status == 200, (url, response.status)
            response.read()
finally:
    server.shutdown()
    server.server_close()
print(
    f"recipes={expected_recipes} html_pages={len(html) + len(de_html)} "
    f"png_images={len(images)} social_cards={len(social_cards)} pagefind_pages={len(pagefind_fragments)} "
    f"http_200_checks={len(urls)} headers=PASS base_url={site_base_url}"
)
print("images=" + json.dumps(images))
print("verification=PASS")
