import unittest
import re
from pathlib import Path
from unittest.mock import patch
import build
import recipe_scaling as scaling


class ScalingTests(unittest.TestCase):
    def test_leading_equipment_temperatures_and_preparation_durations_are_not_amounts(self):
        for text in ['60 °C hot water', '180 °F syrup', '4 hours soaking', '10 minutes preparation',
                     '5 Minuten Vorbereitung', '2 Stunden eingeweicht', '1 l container', '1 Liter Behälter',
                     '20 cm baking pan', '1 glass water', '1 handful nuts', '1 splash milk']:
            with self.subTest(text=text):
                self.assertNotIn('data-quantity=', scaling.ingredient(text, build.inline))

    def test_container_size_is_fixed_even_without_each_suffix(self):
        for text in ['1 can tomatoes (400 g)', '2 Dosen Kichererbsen (400 g)',
                     '2 packets yeast (7 g)', '1 carton milk (1000 g)']:
            with self.subTest(text=text):
                values = re.findall(r'data-quantity="([^\"]+)"', scaling.ingredient(text, build.inline))
                self.assertEqual(values, [text[0]])

    def test_all_recipe_ingredient_presentations_are_metric_and_preserve_methods(self):
        paths = sorted(p for p in Path('.').glob('*.md') if p.name != 'README.md')
        self.assertGreater(len(paths), 30)
        for path in paths + sorted(Path('de').glob('*.md')):
            locale = 'de-CH' if path.parent == Path('de') else 'en'
            recipe = build.parse_recipe(path)
            page = build.build_recipe(recipe, locale)
            matched = re.search(r'<div class="ingredients-list">(.*?)</div>', page)
            self.assertIsNotNone(matched)
            assert matched is not None
            section = matched[1]
            bullets = re.findall(r'^- (.+)$', build.extract_section(recipe.body, 'Ingredients'), re.M)
            self.assertEqual(section.count('<li>'), len(bullets), path)
            # Equipment headings and explanatory source prose are not ingredient lines.
            for item in re.findall(r'<li>(.*?)</li>', section):
                self.assertNotRegex(re.sub('<[^>]+>', '', item), r'\b(?:cups?|Tassen?|oz)\b|°F', str(path))
            method = build.markdown_blocks(build.extract_section(recipe.body, 'Method'), 'method-list')
            self.assertIn(method, page)
            self.assertEqual(page.count('id="recipe-scale"'), 1)
            self.assertEqual(page.count('id="method-scale-note"'), 1)
            self.assertIn('noindex, nofollow', page)

    def test_cup_override_and_approximate_metric_amounts_are_scalable(self):
        source = Path('peanut-butter-oat-cups.md').read_text()
        with patch.object(Path, 'read_text', return_value=source.replace('---\n', '---\ncup_ml: 250\n', 1)):
            recipe = build.parse_recipe(Path('cup-override.md'))
        page = build.build_recipe(recipe)
        self.assertIn('≈ <span data-quantity="250">250</span> ml rolled oats', page)
        self.assertIn('1 cup ≈ 250 ml', page)
        for text, expected in [('≈ 240 ml chocolate (70% cocoa)', ['240']),
                               ('About ≈ 120 ml sauce', ['120']),
                               ('4 Guetzli (insgesamt 20 g)', ['4', '20']),
                               ('2 Äpfel (laut Videobeschreibung etwa 200 g)', ['2','200'])]:
            with self.subTest(text=text):
                self.assertEqual(re.findall(r'data-quantity="([^"]+)"', scaling.ingredient(text, build.inline)), expected)

    def test_metric_presentation_and_provenance(self):
        cases = [
            ('1 cup (95 g) almond flour', '95 g almond flour'),
            ('8 oz (225 g) cottage cheese', '225 g cottage cheese'),
            ('3 oz (about 85 g) Gruyère', 'about 85 g Gruyère'),
            ('1⅔ cups dried dates (about 250 g)', 'about 250 g dried dates'),
            ('2 Tassen Haferflocken (laut Beschreibung etwa 160 g)', 'etwa 160 g Haferflocken'),
            ('About ½ cup / 120 ml of sauce', 'About 120 ml of sauce'),
            ('200 g cheese (about 2 cups / 7 oz)', '200 g cheese'),
            ('270 g crisps (about 3 cups; see Notes)', '270 g crisps'),
            ('1 × 28 oz / approximately 794 g can tomatoes', '1 × 794 g can tomatoes'),
            ('1 Dose à 28 oz / ungefähr 794 g Tomaten', '1 Dose à 794 g Tomaten'),
            ('1/3 cup honey', '≈ 80 ml honey'),
            ('1 Tasse Mehl', '≈ 240 ml Mehl'),
            ('1 cup dark chocolate (70% cocoa)', '≈ 240 ml dark chocolate (70% cocoa)'),
            ('½ cup (130 g) cashews, soaked for 4 hours', '130 g cashews, soaked for 4 hours'),
        ]
        for original, expected in cases:
            with self.subTest(original=original):
                self.assertEqual(scaling.normalize(original), expected)
        self.assertEqual(scaling.normalize('1 cup water', cup_ml=250), '≈ 250 ml water')
        for locale, directory in [('en', '.'), ('de-CH', 'de')]:
            recipe = build.parse_recipe(Path(directory) / 'homemade-oreos.md')
            page = build.build_recipe(recipe, locale)
            self.assertIn('<details class="source-measurements"', page)
            self.assertIn('1 cup (95 g)', page)
            self.assertIn('fda.gov/regulatory-information/', page)

    def test_semicolon_total_weights_preserve_qualifiers_not_pack_weights_or_times(self):
        for text, expected in [
            ('2 tbsp almond butter (about 45 g; optional)', ['2', '45']),
            ('2 EL Mandelmus (etwa 45 g; optional)', ['2', '45']),
            ('2 packets yeast (7 g; optional)', ['2']),
            ('2 Packungen Hefe (7 g; optional)', ['2']),
            ('2 tbsp syrup (45 g per pack; optional)', ['2']),
            ('2 EL Sirup (45 g pro Packung; optional)', ['2']),
            ('2 tbsp syrup (about 45 minutes; optional)', ['2']),
            ('2 EL Sirup (etwa 45 Minuten; optional)', ['2']),
        ]:
            with self.subTest(text=text):
                rendered = scaling.ingredient(text, build.inline)
                self.assertEqual(re.findall(r'data-quantity="([^"]+)"', rendered), expected)
                self.assertEqual(re.sub('<[^>]+>', '', rendered), text)

    def test_nested_equivalents_scale_but_pack_sizes_and_soak_times_do_not(self):
        for text, expected in [('2 apples (about 200 g)', ['2', '200']),
                               ('4 biscuits (20 g total)', ['4','20']),
                               ('1 bunch basil (25–30 g leaves)', ['1','25','30']),
                               ('1 × 794 g can tomatoes', ['1']),
                               ('2 packets yeast (7 g each)', ['2']),
                               ('130 g cashews, soaked for 4 hours', ['130'])]:
            with self.subTest(text=text):
                self.assertEqual(re.findall(r'data-quantity="([^"]+)"', scaling.ingredient(text, build.inline)), expected)

    def test_space_separated_unicode_mixed_fractions_are_complete_tokens(self):
        for token, expected in [('1 ½', 1.5), ('1 ⅔', 1 + 2 / 3)]:
            with self.subTest(token=token):
                self.assertAlmostEqual(scaling.number(token), expected)
                rendered = scaling.ingredient(token + ' tsp salt', build.inline)
                values = re.findall(r'data-quantity="([^"]+)"', rendered)
                self.assertEqual(len(values), 1)
                self.assertAlmostEqual(float(values[0]), expected)
                self.assertIn('>' + token + '</span>', rendered)
                self.assertEqual(re.sub('<[^>]+>', '', rendered), token + ' tsp salt')
        for text in ['1 ⅔ cups flour', '1 ⅔ Tassen Mehl']:
            with self.subTest(text=text):
                normalized = scaling.normalize(text)
                self.assertTrue(normalized.startswith('≈ 400 ml '), normalized)
                self.assertIn('data-quantity="400"', scaling.ingredient(normalized, build.inline))
        rendered = scaling.ingredient('1 ⅔–2 cups oats', build.inline)
        self.assertEqual(re.findall(r'data-quantity="([^"]+)"', rendered), ['1.6666666666666667', '2'])

    def test_fraction_range_locale_and_conservative_boundaries(self):
        cases = [('1 1/2 tsp yeast', ['1.5']), ('1½ TL Salz', ['1.5']),
                 ('1 1/2–2 apples', ['1.5', '2']), ('0–60 ml milk', ['0', '60']),
                 ('A scant ½ tsp salt', ['0.5']), ('Less than ½ tsp powder', ['0.5']),
                 ('Knapp ⅛ TL Salz', ['0.125']), ('Weniger als ¼ TL Salz', ['0.25']),
                 ('Etwa 1,1 g Hefe', ['1.1']), ('Juice of 1/2 lemon', ['0.5']),
                 ('Saft von 1/2 Zitrone', ['0.5']), ('2 packets yeast (7 g each)', ['2']),
                 ('284 g flour (12–14% protein)', ['284']), ('1 cm deep oil', []),
                 ('70% cocoa chocolate', []), ('-2 eggs', []), ('1 Glas Wasser', []),
                 ('A glass water', []), ('handful of nuts', []), ('Splash of vanilla', []),
                 ('1 Oreo cookie, 4 hours chilled', ['1'])]
        for text, expected in cases:
            with self.subTest(text=text):
                rendered = scaling.ingredient(text, build.inline)
                self.assertEqual(re.findall(r'data-quantity="([^"]+)"', rendered), expected)
                self.assertEqual(re.sub('<[^>]+>', '', rendered), text)
        for glyph, value in zip('½⅓⅔¼¾⅛⅜⅝⅞', ['0.5','0.3333333333333333','0.6666666666666666','0.25','0.75','0.125','0.375','0.625','0.875']):
            self.assertIn(f'data-quantity="{value}"', scaling.ingredient(glyph + ' tsp salt', build.inline))

    def test_leading_quantity_is_structured_only_in_ingredients(self):
        page = build.build_recipe(build.parse_recipe(Path('home-oven-pepperoni-pizza.md')))
        self.assertIn('data-quantity="284"', page)
        self.assertIn('12–14% protein', page)
        self.assertNotIn('data-quantity="12"', page)
        self.assertIn('id="recipe-scale"', page)
        self.assertIn('data-recipe-slug="home-oven-pepperoni-pizza"', page)
        self.assertIn('id="scale-controls" hidden', page)


if __name__ == '__main__':
    unittest.main()
