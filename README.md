# Recipe Collection

Markdown recipes collected from videos and other sources.

## Desserts

- [Homemade Snickers Bars](homemade-snickers-bars.md) — KineleVital
- [Homemade Ferrero Rocher–Style Balls](homemade-ferrero-rocher-style-balls.md) — KineleVital
- [Peanut Butter Oat Cups](peanut-butter-oat-cups.md) — Dessert Loop
- [Pistachio Chocolate-Covered Scoops](pistachio-chocolate-covered-scoops.md) — KineleVital
- [Chocolate Biscoff Protein Bowl](chocolate-biscoff-protein-bowl.md) — Barham Barzinjy

## Savoury

- [Crispy Tomato & Olive Oil Bread](crispy-tomato-olive-oil-bread.md) — Pascha TV

Each recipe keeps its original source link, creator attribution, access date, and notes about details the source did not specify.

## Local development

```bash
npm ci
npm test
npm run build
npm run verify
npx pagefind --site _site --serve
```

`npm run build` generates the static site and a fully client-side Pagefind index in `_site/`. Search requires serving `_site/` over HTTP rather than opening `index.html` directly.
