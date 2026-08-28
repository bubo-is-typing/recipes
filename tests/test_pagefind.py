import json
import unittest
from pathlib import Path

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

    def test_index_uses_accessible_pagefind_searchbox(self):
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

    def test_package_build_runs_pagefind_after_static_generation(self):
        package_path = Path(__file__).parents[1] / "package.json"
        package = json.loads(package_path.read_text())
        self.assertEqual(package["devDependencies"]["pagefind"], "1.5.2")
        self.assertEqual(package["scripts"]["build"], "python3 build.py && pagefind --site _site")
        self.assertEqual(package["scripts"]["test"], "python3 -m unittest discover -s tests -v")
        self.assertEqual(package["scripts"]["verify"], "python3 verify_site.py")


if __name__ == "__main__":
    unittest.main()
