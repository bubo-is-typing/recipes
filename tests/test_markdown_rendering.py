import unittest
from pathlib import Path

import build


class MarkdownRenderingTests(unittest.TestCase):
    def test_recipe_method_renders_bold_emphasis(self):
        recipe_path = Path(__file__).parents[1] / "home-oven-pepperoni-pizza.md"
        page = build.build_recipe(build.parse_recipe(recipe_path))

        self.assertIn("<strong>About three days before baking:</strong>", page)
        self.assertIn("<strong>10–11 minutes in total</strong>", page)
        self.assertNotIn("**About three days before baking:**", page)

    def test_ingredients_render_italic_with_nested_bold(self):
        recipe_path = Path(__file__).parents[1] / "home-oven-pepperoni-pizza.md"
        page = build.build_recipe(build.parse_recipe(recipe_path))

        self.assertIn(
            "<em>These one-pizza weights are from Dough Guy’s calculator set to "
            "<strong>1 pizza, 16 inches, regular thickness</strong>.",
            page,
        )
        self.assertNotIn("*These one-pizza weights", page)


if __name__ == "__main__":
    unittest.main()
