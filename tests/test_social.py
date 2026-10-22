import dataclasses
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build


class SocialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.en = build.parse_recipe(build.ROOT / 'apple-waffles-with-cinnamon-sugar.md')
        cls.de = build.parse_recipe(build.ROOT / 'de/apple-waffles-with-cinnamon-sugar.md')

    def test_recipe_metadata_localized_and_absolute_for_both_bases(self):
        for base, origin in (('/', 'https://recipes.bubo.page'), ('/recipes/', 'https://bubo-is-typing.github.io')):
            with self.subTest(base=base), patch.dict(os.environ, {'SITE_BASE_URL': base, 'SITE_ORIGIN': origin}):
                for recipe, locale, prefix in ((self.en, 'en', ''), (self.de, 'de-CH', 'de/')):
                    page = build.build_recipe(recipe, locale)
                    canonical = f'{origin}{base}{prefix}{recipe.slug}{"" if base == "/" else ".html"}'
                    image = f'{origin}{base}og/{prefix}{recipe.slug}.png'
                    for tag in (f'<meta property="og:url" content="{canonical}">',
                                f'<meta property="og:image" content="{image}">',
                                f'<meta name="twitter:image" content="{image}">',
                                f'<meta property="og:title" content="{recipe.title}">',
                                '<meta property="og:type" content="article">',
                                '<meta property="og:image:width" content="1200">',
                                '<meta property="og:image:height" content="630">',
                                '<meta property="og:image:type" content="image/png">',
                                f'<meta property="og:locale" content="{"de_CH" if locale == "de-CH" else "en_US"}">',
                                f'<meta property="og:site_name" content="{build.UI[locale]["site"]}">',
                                '<meta name="twitter:card" content="summary_large_image">'):
                        self.assertIn(tag, page)
                    self.assertIn('property="og:description"', page)
                    self.assertIn('name="twitter:description"', page)
                    self.assertIn('property="og:image:alt"', page)
                    self.assertIn(f'<meta name="twitter:title" content="{recipe.title}">', page)
                    self.assertIn('name="robots" content="noindex, nofollow', page)

    def test_social_png_is_localized_deterministic_and_falls_back_without_photo(self):
        photo_free = dataclasses.replace(self.en, image=None, image_alt=None, title='A very long title with ünicode accents and several descriptive words that need wrapping')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for recipe, locale in ((self.en, 'en'), (self.de, 'de-CH'), (photo_free, 'en')):
                path = output / locale / 'card.png'
                build.render_social_card(recipe, locale, path)
                first = path.read_bytes()
                self.assertEqual(first[:8], b'\x89PNG\r\n\x1a\n')
                self.assertEqual(struct.unpack('>II', first[16:24]), (1200, 630))
                build.render_social_card(recipe, locale, path)
                self.assertEqual(first, path.read_bytes())
                if recipe.image:
                    from PIL import Image, ImageChops
                    with Image.open(path) as image:
                        self.assertIsNotNone(ImageChops.difference(image.convert('RGB').crop((0, 0, 510, 630)), Image.new('RGB', (510, 630), '#fbf8f2')).getbbox())

    def test_catalogue_has_own_localized_social_card(self):
        for base, origin in (('/', 'https://recipes.bubo.page'), ('/recipes/', 'https://bubo-is-typing.github.io')):
            with patch.dict(os.environ, {'SITE_BASE_URL': base, 'SITE_ORIGIN': origin}):
                for locale, prefix in (('en', ''), ('de-CH', 'de/')):
                    page = build.build_index([self.en], locale)
                    self.assertIn(f'{origin}{base}og/{prefix}index.png', page)
                    canonical = f'{origin}{base}{prefix}{"" if base == "/" else "index.html"}'
                    self.assertIn(f'<meta property="og:url" content="{canonical}">', page)

    def test_build_generates_cards_for_all_pairs_and_catalogues(self):
        paths = [p for p in build.ROOT.glob('*.md') if p.name != 'README.md']
        with tempfile.TemporaryDirectory() as tmp, patch.object(build, 'OUT', Path(tmp) / 'site'):
            build.main()
            cards = sorted((build.OUT / 'og').rglob('*.png'))
            self.assertEqual(len(cards), 2 * len(paths) + 2)
            for path in paths:
                self.assertTrue((build.OUT / 'og' / f'{path.stem}.png').exists())
                self.assertTrue((build.OUT / 'og' / 'de' / f'{path.stem}.png').exists())
            self.assertTrue((build.OUT / 'og' / 'index.png').exists())
            self.assertTrue((build.OUT / 'og' / 'de' / 'index.png').exists())
