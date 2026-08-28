#!/usr/bin/env python3
import http.server
import json
import os
import re
import socketserver
import struct
import threading
import urllib.request
from pathlib import Path

root = Path(__file__).parent
recipes = sorted(p for p in root.glob("*.md") if p.name != "README.md")
expected_recipes = len(recipes)
assert expected_recipes > 0
images = []
for recipe in recipes:
    text = recipe.read_text()
    match = re.search(r"^image:\s*(\S+)", text, re.M)
    assert match, recipe
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
assert len(html) == expected_recipes + 1, len(html)
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
assert len(pagefind_fragments) == expected_recipes, len(pagefind_fragments)

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
    + [f"/assets/images/{name}" for name, _ in images]
    + ["/assets/style.css", "/assets/site.js"]
    + [f"/pagefind/{path.name}" for path in required_pagefind_assets]
    + [f"/pagefind/fragment/{path.name}" for path in pagefind_fragments]
)
for url in urls:
    with urllib.request.urlopen(base + url, timeout=10) as response:
        assert response.status == 200, (url, response.status)
        response.read()
server.shutdown()
server.server_close()
print(
    f"recipes={expected_recipes} html_pages={len(html)} "
    f"png_images={len(images)} pagefind_pages={len(pagefind_fragments)} "
    f"http_200_checks={len(urls)}"
)
print("images=" + json.dumps(images))
print("verification=PASS")
