# Recipe Collection

Markdown recipes collected from videos and other sources.

## Breakfast

- [Magnum-Style Chocolate Chia Pudding](magnum-style-chocolate-chia-pudding.md) — Juliana Ksander
- [High-Protein Tiramisu Oats](high-protein-tiramisu-oats.md) — Fitness.Compani0n
- [Date Caramel Blended Oats](date-caramel-blended-oats.md) — Liz Douglas

## Desserts

- [Peanut Butter Chickpea Chocolate Chip Cookies](peanut-butter-chickpea-chocolate-chip-cookies.md) — Stefan Bodegrajac
- [Homemade Oreos](homemade-oreos.md) — KineleVital
- [Homemade Snickers Bars](homemade-snickers-bars.md) — KineleVital
- [Homemade Ferrero Rocher–Style Balls](homemade-ferrero-rocher-style-balls.md) — KineleVital
- [Peanut Butter Oat Cups](peanut-butter-oat-cups.md) — Dessert Loop
- [Pistachio Chocolate-Covered Scoops](pistachio-chocolate-covered-scoops.md) — KineleVital
- [Chocolate Biscoff Protein Bowl](chocolate-biscoff-protein-bowl.md) — Barham Barzinjy
- [Frozen Peanut Butter Yogurt Bites](frozen-peanut-butter-yogurt-bites.md) — KineleVital
- [Homemade Cookie Dough Ice Cream Bars](homemade-cookie-dough-ice-cream-bars.md) — KineleVital
- [Fudge Brownie Cheesecake Bars](fudge-brownie-cheesecake-bars.md) — Stefan Bodegrajac
- [Whole-Lime Loaf Cake](whole-lime-loaf-cake.md) — Jose.elcook
- [High-Protein Frozen Yogurt Bars](high-protein-frozen-yogurt-bars.md) — Adam Wolfe
- [High-Protein Blueberry Lemon Cheesecake](high-protein-blueberry-lemon-cheesecake.md) — We Are Recipes
- [Apple Waffles with Cinnamon Sugar](apple-waffles-with-cinnamon-sugar.md) — Foodwerk
- [High-Protein Chocolate Crispy Cakes](high-protein-chocolate-crispy-cakes.md) — Maria Lucey
- [Greek Yogurt Brownie Batter](greek-yogurt-brownie-batter.md) — Juliana Ksander
- [High-Protein Frosted Chocolate Oreo Loaf](high-protein-frosted-chocolate-oreo-loaf.md) — Christopher Kai Yu

## Savoury

- [Four-Ingredient Parmesan Cheese Crackers](four-ingredient-parmesan-cheese-crackers.md) — Joey Wellness
- [Home-Oven Pepperoni Pizza with 3-Day Dough](home-oven-pepperoni-pizza.md) — Dough Guy
- [High-Protein Rice-Paper Chicken Nuggets](high-protein-rice-paper-chicken-nuggets.md) — MAX (@maxxpane; original video credited to @panaceapalm)
- [Creamy Boursin Chicken Orzo Bake](creamy-boursin-chicken-orzo-bake.md) — Unknown creator (user-provided screenshot)
- [Cotton-Soft Kiflice (Balkan Crescent Rolls)](soft-kiflice-balkan-crescent-rolls.md) — Kuhinja Sabi
- [Upside-Down Tomato Tart with Burrata](upside-down-tomato-tart-with-burrata.md) — Bruno Pecorino
- [Crispy Tomato & Olive Oil Bread](crispy-tomato-olive-oil-bread.md) — Pascha TV
- [Crispy Pan-Fried Onigirazu](crispy-pan-fried-onigirazu.md) — Wild Planet Foods

## Drinks

- [Sprite Black Tea with Lemon](sprite-black-tea-with-lemon.md) — Sarah Betts

Each recipe keeps its original source link, creator attribution, access date, and notes about details the source did not specify.

## Languages

The English recipe Markdown at the repository root is the source-faithful original. Add a Swiss Standard German translation at `de/<same-slug>.md` for **every** recipe; keep creator names, source links, dates, tags, image paths and quantities aligned while translating the title, image alt text, ingredients, method, notes and visible source descriptions. Write German with `ss` rather than `ß`. The build checks for one matching translation per English recipe and produces both language versions.

When adding a recipe, add its English Markdown, its `de/` translation and a link here before publishing. Review both languages, run `npm test`, `npm run build` and `npm run verify`, then check the English and German pages, catalogue, search, and language switch after deployment. An explicit language choice is remembered in a cookie; otherwise the site uses the browser’s preferred language.

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
npm test
npm run build
npm run verify
npx pagefind --site _site --serve
```

`npm run build` generates the static site and a fully client-side Pagefind index in `_site/`. Search requires serving `_site/` over HTTP rather than opening `index.html` directly.

The build also generates localized 1200×630 social cards in `_site/og/` and `_site/og/de/` for every recipe and both catalogues. Cards use each recipe's existing image where available; image-free recipes receive typography-only cards. The bundled Fraunces and DM Sans font files are licensed under their corresponding `fonts/OFL-*.txt` licenses (Google Fonts source revision `45e3d5269e4a17d823f6d84470bc084dc5ae46f6`). The cards reuse recipe images; the recipe pages retain their existing source attribution. No new photography is introduced.

Open Graph URLs use `https://recipes.bubo.page/` for a root build and `https://bubo-is-typing.github.io/recipes/` for the default subpath build. Set `SITE_ORIGIN` to an HTTPS origin if hosting under another domain. The existing `noindex` and `X-Robots-Tag` policy is unchanged; some social crawlers may therefore decline to show a preview despite valid metadata.

## Deployment

The production site is https://recipes.bubo.page/ on Cloudflare Pages. Every push to `main` runs the test suite, builds and verifies both hosting variants, then deploys Cloudflare Pages and the GitHub Pages fallback through `.github/workflows/pages.yml`.

For a manual Cloudflare deployment, build and verify at the domain root before uploading:

```bash
rm -rf _site
SITE_BASE_URL=/ npm run build
SITE_BASE_URL=/ npm run verify
npx wrangler pages deploy _site --project-name recipes --branch main
```

The default build base remains `/recipes/` so the existing GitHub Pages deployment continues to work as a migration fallback.
