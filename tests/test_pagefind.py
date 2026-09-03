import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import build


class PagefindBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        recipe_path = next(path for path in sorted(Path(__file__).parents[1].glob("*.md")) if path.name != "README.md")
        cls.recipe = build.parse_recipe(recipe_path)

    def test_recipe_page_marks_only_recipe_content_for_indexing(self):
        page = build.build_recipe(self.recipe)
        self.assertIn('<article class="recipe" data-pagefind-body>', page)
        self.assertNotIn('<main class="recipe-main" id="main" data-pagefind-body>', page)

    def test_index_uses_accessible_pagefind_searchbox_with_default_base_url(self):
        with patch.dict(os.environ, {}, clear=True):
            page = build.build_index([self.recipe])
        self.assertIn('<link rel="stylesheet" href="pagefind/pagefind-component-ui.css">', page)
        self.assertIn('<script src="pagefind/pagefind-component-ui.js" type="module"></script>', page)
        self.assertIn(
            '<pagefind-config base-url="/recipes/" bundle-path="/recipes/pagefind/"></pagefind-config>',
            page,
        )
        self.assertIn(
            '<pagefind-searchbox placeholder="Search recipes and ingredients…" '
            'show-sub-results></pagefind-searchbox>',
            page,
        )
        self.assertNotIn('max-results=', page)
        self.assertNotIn('id="recipe-search"', page)

    def test_index_uses_root_pagefind_paths_for_cloudflare_pages(self):
        with patch.dict(os.environ, {"SITE_BASE_URL": "/"}, clear=True):
            page = build.build_index([self.recipe])
        self.assertIn(
            '<pagefind-config base-url="/" bundle-path="/pagefind/"></pagefind-config>',
            page,
        )

    def test_site_base_url_normalizes_leading_and_trailing_slashes(self):
        for value in ("recipes", "/recipes", "recipes/", "///recipes///"):
            with self.subTest(value=value):
                self.assertEqual(build.normalize_site_base_url(value), "/recipes/")
        for value in ("", "/", "///"):
            with self.subTest(value=value):
                self.assertEqual(build.normalize_site_base_url(value), "/")

    def test_cloudflare_headers_cover_all_paths(self):
        self.assertEqual(
            build.SECURITY_HEADERS,
            """/*
  X-Robots-Tag: noindex, nofollow, noarchive, nosnippet, noimageindex
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
""",
        )
        self.assertNotIn("Content-Security-Policy", build.SECURITY_HEADERS)

    def test_all_generated_pages_block_search_engine_indexing(self):
        directives = (
            '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">',
            '<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex">',
        )
        for page in (build.build_index([self.recipe]), build.build_recipe(self.recipe)):
            for directive in directives:
                self.assertIn(directive, page)

    def test_custom_not_found_page_blocks_search_engine_indexing(self):
        page = build.build_not_found()
        self.assertIn(
            '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">',
            page,
        )
        self.assertIn(
            '<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex">',
            page,
        )

    def test_package_build_runs_pagefind_after_static_generation(self):
        package_path = Path(__file__).parents[1] / "package.json"
        package = json.loads(package_path.read_text())
        self.assertEqual(package["devDependencies"]["pagefind"], "1.5.2")
        self.assertEqual(package["scripts"]["build"], "python3 build.py && pagefind --site _site")
        self.assertEqual(package["scripts"]["test"], "python3 -m unittest discover -s tests -v")
        self.assertEqual(package["scripts"]["verify"], "python3 verify_site.py")


if __name__ == "__main__":
    unittest.main()
