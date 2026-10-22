import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build


class BilingualBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = next(p for p in sorted(build.ROOT.glob('*.md')) if p.name != 'README.md')
        cls.english = build.parse_recipe(cls.path)

    def test_translations_require_matching_slugs_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            de = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'Missing German translation'):
                build.load_translations([self.path], de)
            text = self.path.read_text().replace('title: ' + self.english.title, 'title: Deutsches Rezept', 1)
            (de / self.path.name).write_text(text)
            result = build.load_translations([self.path], de)
            self.assertEqual(result[0].title, 'Deutsches Rezept')
            (de / 'orphan.md').write_text(text)
            with self.assertRaisesRegex(ValueError, 'Unexpected German translation'):
                build.load_translations([self.path], de)
            (de / 'orphan.md').unlink()
            (de / self.path.name).write_text(text.replace('## Method', '## Anleitung'))
            with self.assertRaisesRegex(ValueError, 'Method'):
                build.load_translations([self.path], de)

    def test_german_recipe_has_local_chrome_asset_paths_and_switch(self):
        page = build.build_recipe(self.english, locale='de-CH')
        self.assertIn('<html lang="de-CH">', page)
        self.assertIn('href="../assets/style.css?v=', page)
        self.assertIn('src="../assets/site.js?v=', page)
        self.assertIn('href="index.html"', page)
        self.assertIn(f'href="../{self.english.slug}.html"', page)
        self.assertIn('aria-current="page"', page)
        self.assertIn('Zutaten', page)
        self.assertIn('Zubereitung', page)
        self.assertIn('Kochmodus', page)
        self.assertIn('Rezept drucken', page)
        self.assertIn('Quellen', page)
        if self.english.image:
            self.assertIn(f'src="../{self.english.image}"', page)
        self.assertIn('name="robots" content="noindex', page)
        self.assertIn('data-pagefind-body', page)

    def test_german_catalogue_localizes_controls_and_search(self):
        page = build.build_index([self.english], locale='de-CH')
        self.assertIn('href="../assets/style.css?v=', page)
        self.assertIn('<pagefind-searchbox placeholder="Rezepte und Zutaten suchen…"', page)
        self.assertIn('bundle-path="/recipes/pagefind/"', page)
        self.assertIn('Älteste zuerst', page)
        self.assertIn('Alle Rezepte', page)
        self.assertIn('Keine Rezepte gefunden', page)
        self.assertIn(f'href="{self.english.slug}.html"', page)
        self.assertIn('data-count-all="Alle', page)
        self.assertIn('aria-current="page"', page)

    def test_not_found_uses_configured_base_for_both_locales(self):
        with patch.dict('os.environ', {'SITE_BASE_URL': '/'}, clear=True):
            german = build.build_not_found(locale='de-CH')
            english = build.build_not_found()
        self.assertIn('href="/de/"', german)
        self.assertIn('href="/"', english)
        self.assertNotIn('href="/recipes/"', english)
        self.assertIn('<html lang="de-CH">', german)

    def test_german_creator_context_is_translated_without_altering_attribution(self):
        unknown = build.parse_recipe(build.ROOT / 'de' / 'creamy-boursin-chicken-orzo-bake.md')
        original_credit = build.parse_recipe(build.ROOT / 'de' / 'high-protein-rice-paper-chicken-nuggets.md')
        page = build.build_recipe(unknown, locale='de-CH')
        card = build.card(original_credit, 0, locale='de-CH')
        self.assertIn('Unbekannte Urheberschaft', page)
        self.assertNotIn('user-provided screenshot', page)
        self.assertIn('href="#sources-heading"', page)
        self.assertIn('@panaceapalm', card)
        self.assertNotIn('credits original video to', card)

    def test_new_german_filter_tags_require_a_visible_translation(self):
        with self.assertRaisesRegex(ValueError, 'German tag label'):
            build.tag_label('new-course', locale='de-CH')


if __name__ == '__main__':
    unittest.main()
