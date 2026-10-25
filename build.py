#!/usr/bin/env python3
"""Build the recipe collection into a dependency-free static site."""

from __future__ import annotations

import html
import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
ASSETS = ROOT / "assets"
FONTS = ROOT / "fonts"
DEFAULT_SITE_BASE_URL = "/recipes/"
DE = "de-CH"
UI = {
    "en": dict(site="The Recipe Index", edition="A small-batch recipe journal", skip="Skip to content", footer="Collected with care, cooked with curiosity.", footer_note="Recipes retain their original creator attribution and sources.", photo="Photo coming soon", by="By", ingredients="Ingredients", ingredient_unit="ingredients", steps="steps", view="View recipe", open="Open", all="All recipes", hero_eyebrow="Volume 01 · Something good", hero_title="Recipes worth<br><em>making again.</em>", hero_intro="A considered collection of recipes worth keeping—sourced carefully and ready for the kitchen.", inside="recipes<br>inside", browse="Browse the collection", box="The recipe box", search="Search recipes and ingredients…", filter="Filter recipes by tag", show_all="Showing all {n} recipes", found_one="{n} recipe found", found_many="{n} recipes found", date="Date added", newest="Newest first", oldest="Oldest first", empty="No recipes found", empty_hint="Try another word or clear the selected filter.", breadcrumb="Breadcrumb", recipe="Recipe", method="Method", collected="Collected", actions="Recipe actions", cook="Cooking mode", print="Print recipe", source="Original source", before="Before you begin", notes="Cook’s notes", sources="Sources & attribution", exit="Exit", notfound="Not found", notfound_title="This page is<br><em>off the menu.</em>", return_link="Return to the recipe index", notfound_meta="The requested recipe page was not found.", page_title="Page not found"),
    DE: dict(site="Das Rezeptverzeichnis", edition="Ein Rezeptjournal mit kleiner Auswahl", skip="Zum Inhalt springen", footer="Mit Sorgfalt gesammelt, mit Neugier gekocht.", footer_note="Die Rezepte behalten die Angaben zu Urhebern und Quellen.", photo="Foto folgt", by="Von", ingredients="Zutaten", ingredient_unit="Zutaten", steps="Schritte", view="Rezept ansehen", open="Öffnen:", all="Alle Rezepte", hero_eyebrow="Ausgabe 01 · Etwas Gutes", hero_title="Rezepte zum<br><em>Immer-wieder-Kochen.</em>", hero_intro="Eine sorgfältig zusammengestellte Rezeptsammlung – gut dokumentiert und bereit für die Küche.", inside="Rezepte<br>in der Sammlung", browse="Sammlung entdecken", box="Die Rezeptsammlung", search="Rezepte und Zutaten suchen…", filter="Rezepte nach Stichwort filtern", show_all="Alle {n} Rezepte", found_one="{n} Rezept gefunden", found_many="{n} Rezepte gefunden", date="Hinzugefügt", newest="Neueste zuerst", oldest="Älteste zuerst", empty="Keine Rezepte gefunden", empty_hint="Versuche einen anderen Suchbegriff oder entferne den Filter.", breadcrumb="Brotkrumennavigation", recipe="Rezept", method="Zubereitung", collected="Erfasst", actions="Rezeptaktionen", cook="Kochmodus", print="Rezept drucken", source="Originalquelle", before="Vor dem Start", notes="Hinweise zum Rezept", sources="Quellen und Urheberangaben", exit="Beenden", notfound="Nicht gefunden", notfound_title="Diese Seite steht<br><em>nicht auf der Karte.</em>", return_link="Zur Rezeptsammlung zurückkehren", notfound_meta="Die angeforderte Rezeptseite wurde nicht gefunden.", page_title="Seite nicht gefunden"),
}
DE_TAGS = dict(Balkan="Balkan", apple="Apfel", avocado="Avocado", baked="gebacken", biscoff="Biscoff", blueberry="Heidelbeere", boursin="Boursin", bread="Brot", breakfast="Frühstück", burrata="Burrata", cake="Kuchen", caramel="Karamell", cashew="Cashew", cheese="Käse", cheesecake="Käsekuchen", chia="Chia", chicken="Poulet", chickpeas="Kichererbsen", chocolate="Schokolade", cinnamon="Zimt", coconut="Kokos", coffee="Kaffee", cookies="Guetzli", crackers="Cracker", crispy="knusprig", dessert="Dessert", drink="Getränk", egg="Ei", frozen="gefroren", hazelnut="Haselnuss", lemon="Zitrone", lime="Limette", nuggets="Nuggets", oats="Hafer", onigirazu="Onigirazu", oreo="Oreo", orzo="Orzo", pasta="Pasta", pepperoni="Pepperoni", pistachio="Pistazie", pizza="Pizza", quick="schnell", rice="Reis", savoury="herzhaft", sesame="Sesam", snack="Snack", strawberry="Erdbeere", tart="Tarte", tea="Tee", tomato="Tomate", tomatoes="Tomaten", tuna="Thunfisch", vegan="vegan", waffle="Waffel", walnut="Walnuss", yoghurt="Joghurt", yogurt="Joghurt", courgette="Zucchetti")
DE_TAGS.update({"air-fryer": "Heissluftfritteuse", "cold-ferment": "lange Teigführung", "cookie-dough": "Guetzliteig", "cottage-cheese": "Hüttenkäse", "date-caramel": "Dattelkaramell", "freezer-friendly": "zum Einfrieren", "gluten-free": "glutenfrei", "greek-yogurt": "griechischer Joghurt", "high-fibre": "ballaststoffreich", "high-protein": "proteinreich", "ice-cream": "Glace", "kid-friendly": "kinderfreundlich", "loaf-cake": "Kastenkuchen", "muffins": "Muffins", "no-bake": "ohne Backen", "oat-flour": "Hafermehl", "pasta-bake": "Nudelauflauf", "peanut-butter": "Erdnussbutter", "puff-pastry": "Blätterteig", "rice-paper": "Reispapier"})
DE_CREATOR_CONTEXT = {
    "Unknown creator (user-provided screenshot)": "Unbekannte Urheberschaft (bereitgestellter Screenshot)",
    "MAX (@maxxpane; credits original video to @panaceapalm)": "MAX (@maxxpane; Originalvideo: @panaceapalm)",
    "FirstTakeHadrian (inspired by @homestead.wellness.daily)": "FirstTakeHadrian (inspiriert von @homestead.wellness.daily)",
}

def creator_label(creator: str, locale: str = "en") -> str:
    return DE_CREATOR_CONTEXT.get(creator, creator) if locale == DE else creator


def tag_label(tag: str, locale: str = "en") -> str:
    if locale == DE:
        if tag not in DE_TAGS:
            raise ValueError(f"Missing German tag label: {tag}; add it to DE_TAGS in build.py")
        return DE_TAGS[tag]
    return tag.replace("-", " ")
SECURITY_HEADERS = """/*
  X-Robots-Tag: noindex, nofollow, noarchive, nosnippet, noimageindex
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
"""


def normalize_site_base_url(value: str | None = None) -> str:
    """Return an absolute base path with exactly one leading/trailing slash."""
    raw_value = os.environ.get("SITE_BASE_URL", DEFAULT_SITE_BASE_URL) if value is None else value
    path = raw_value.strip().strip("/")
    return f"/{path}/" if path else "/"


def social_metadata(title: str, description: str, locale: str, slug: str | None, image_alt: str) -> str:
    base = normalize_site_base_url()
    origin = os.environ.get("SITE_ORIGIN", "https://recipes.bubo.page" if base == "/" else "https://bubo-is-typing.github.io").rstrip("/")
    if not origin.startswith("https://") or "/" in origin[8:]:
        raise ValueError("SITE_ORIGIN must be an HTTPS origin without a path")
    language = "de/" if locale == DE else ""
    name = (f"{slug}{'' if base == '/' else '.html'}" if slug else ("" if base == "/" else "index.html"))
    card = f"{slug}.png" if slug else "index.png"
    url = f"{origin}{base}{language}{name}"
    image = f"{origin}{base}og/{language}{card}"
    esc = lambda value: html.escape(value, quote=True)
    fields = [("property", "og:type", "article" if slug else "website"),
              ("property", "og:locale", "de_CH" if locale == DE else "en_US"),
              ("property", "og:site_name", UI[locale]["site"]),
              ("property", "og:title", title), ("property", "og:description", description),
              ("property", "og:url", url), ("property", "og:image", image),
              ("property", "og:image:type", "image/png"), ("property", "og:image:width", "1200"),
              ("property", "og:image:height", "630"), ("property", "og:image:alt", image_alt),
              ("name", "twitter:card", "summary_large_image"), ("name", "twitter:image", image),
              ("name", "twitter:title", title), ("name", "twitter:description", description)]
    return "\n  ".join(f'<meta {attr}="{key}" content="{esc(value)}">' for attr, key, value in fields)


def render_social_card(recipe: Recipe | None, locale: str, output: Path) -> None:
    """Render a reproducible branded card from the actual recipe photograph (if present)."""
    title = recipe.title if recipe else UI[locale]["site"]
    with_photo = bool(recipe and recipe.image)
    left = 510 if with_photo else 0
    canvas = Image.new("RGB", (1200, 630), "#fbf8f2")
    if with_photo:
        assert recipe is not None and recipe.image is not None
        source = ROOT / recipe.image
        with Image.open(source) as photo:
            canvas.paste(ImageOps.fit(photo.convert("RGB"), (510, 630), method=Image.Resampling.LANCZOS), (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((left, 0, left + 9, 630), fill="#b44e36")
    x = left + 72
    width = 1200 - x - 68
    label_font = ImageFont.truetype(FONTS / "DMSans.ttf", 23)
    draw.text((x, 67), UI[locale]["site"].upper(), font=label_font, fill="#b44e36")
    draw.line((x, 111, x + min(width, 405), 111), fill="#d9b5a6", width=2)

    def wrap(font: ImageFont.FreeTypeFont) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in title.split():
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    for size in range(78, 27, -2):
        title_font = ImageFont.truetype(FONTS / "Fraunces.ttf", size)
        title_font.set_variation_by_name("Bold")
        lines = wrap(title_font)
        line_height = int(size * 1.14)
        if lines and len(lines) * line_height <= 380 and all(draw.textlength(line, font=title_font) <= width for line in lines):
            break
    else:
        raise ValueError(f"Social title does not fit: {title}")
    y = 145 + (380 - len(lines) * line_height) // 2
    for line in lines:
        draw.text((x, y), line, font=title_font, fill="#27231f", stroke_width=0)
        y += line_height
    draw.line((x, 552, x + 44, 552), fill="#b44e36", width=4)
    draw.text((x + 60, 539), UI[locale]["edition"], font=ImageFont.truetype(FONTS / "DMSans.ttf", 20), fill="#645a52")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=False)


@dataclass
class Recipe:
    slug: str
    title: str
    creator: str
    source_url: str
    accessed: str
    tags: list[str]
    image: str | None
    image_alt: str | None
    body: str

    @property
    def display_tags(self) -> list[str]:
        return [tag for tag in self.tags if tag not in {"recipe", "dessert"}]

    @property
    def ingredient_count(self) -> int:
        section = extract_section(self.body, "Ingredients")
        return len(re.findall(r"(?m)^- ", section))

    @property
    def step_count(self) -> int:
        section = extract_section(self.body, "Method")
        return len(re.findall(r"(?m)^\d+\. ", section))


def parse_recipe(path: Path) -> Recipe:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError(f"{path.name}: expected YAML-like frontmatter")
    raw_meta, body = match.groups()
    meta: dict[str, str | list[str]] = {}
    current_list: str | None = None
    for line in raw_meta.splitlines():
        item = re.match(r"^\s+-\s+(.+)$", line)
        if item and current_list:
            assert isinstance(meta[current_list], list)
            meta[current_list].append(item.group(1).strip())
            continue
        key_value = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if key_value:
            key, value = key_value.groups()
            if value:
                meta[key] = value.strip()
                current_list = None
            else:
                meta[key] = []
                current_list = key
    required = ("title", "source_creator", "source_url", "accessed", "tags")
    missing = [key for key in required if key not in meta]
    if missing:
        raise ValueError(f"{path.name}: missing frontmatter: {', '.join(missing)}")
    if ("image" in meta) != ("image_alt" in meta):
        raise ValueError(f"{path.name}: image and image_alt must be supplied together")
    return Recipe(
        slug=path.stem,
        title=str(meta["title"]),
        creator=str(meta["source_creator"]),
        source_url=str(meta["source_url"]).strip('"'),
        accessed=str(meta["accessed"]),
        tags=list(meta["tags"]),
        image=str(meta["image"]) if "image" in meta else None,
        image_alt=str(meta["image_alt"]) if "image_alt" in meta else None,
        body=body.strip(),
    )


def load_translations(english_paths: list[Path], directory: Path) -> list[Recipe]:
    """Enforce a matching translated recipe with preserved source metadata."""
    expected = {path.name for path in english_paths}
    actual = {path.name for path in directory.glob("*.md")}
    missing, extra = sorted(expected - actual), sorted(actual - expected)
    if missing:
        raise ValueError(f"Missing German translation: {', '.join(missing)}")
    if extra:
        raise ValueError(f"Unexpected German translation: {', '.join(extra)}")
    translations = []
    for path in english_paths:
        original, translated = parse_recipe(path), parse_recipe(directory / path.name)
        for field in ("creator", "source_url", "accessed", "tags", "image"):
            if getattr(original, field) != getattr(translated, field):
                raise ValueError(f"{path.name}: German {field} must match English")
        for section in ("Ingredients", "Method", "Notes", "Sources"):
            if not re.search(rf"(?m)^## {section}\s*$", translated.body):
                raise ValueError(f"{path.name}: German translation requires ## {section}")
        translations.append(translated)
    return translations


def extract_section(markdown: str, name: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", markdown)
    return match.group(1).strip() if match else ""


def inline(text: str) -> str:
    links = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")

    def render_text(value: str) -> str:
        escaped = html.escape(value, quote=False)
        escaped = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", escaped)
        return re.sub(r"(?<!\*)\*(?=\S)(.+?)(?<=\S)\*(?!\*)", r"<em>\1</em>", escaped)

    parts: list[str] = []
    offset = 0
    for match in links.finditer(text):
        parts.append(render_text(text[offset:match.start()]))
        parts.append(
            f'<a href="{html.escape(match.group(2), quote=True)}" rel="noopener noreferrer">'
            f'{render_text(match.group(1))}</a>'
        )
        offset = match.end()
    parts.append(render_text(text[offset:]))
    return "".join(parts)


def markdown_blocks(markdown: str, section_class: str = "") -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    for line in lines + [""]:
        stripped = line.strip()
        heading = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        bullet = re.match(r"^-\s+(.+)$", stripped)
        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if heading:
            flush_paragraph(); close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif bullet or ordered:
            flush_paragraph()
            desired = "ul" if bullet else "ol"
            if list_type != desired:
                close_list(); output.append(f"<{desired}>"); list_type = desired
            content = (bullet or ordered).group(1)
            output.append(f"<li><span>{inline(content)}</span></li>")
        elif not stripped:
            flush_paragraph(); close_list()
        else:
            close_list(); paragraph.append(stripped)
    class_attr = f' class="{section_class}"' if section_class else ""
    return f"<div{class_attr}>{''.join(output)}</div>"


def shell(title: str, description: str, content: str, *, page_class: str = "", locale: str = "en", slug: str | None = None, image_alt: str = "") -> str:
    t = UI[locale]
    is_not_found = page_class == "not-found-page"
    prefix = normalize_site_base_url() if is_not_found else ("../" if locale == DE else "")
    if is_not_found:
        english_link = f"{prefix}404.html"
        german_link = f"{prefix}de/404.html"
    else:
        english_link = f"{prefix}{slug}.html" if slug else f"{prefix}index.html"
        german_link = f"{slug}.html" if locale == DE and slug else (f"de/{slug}.html" if slug else ("index.html" if locale == DE else "de/index.html"))
    home_link = (normalize_site_base_url() + ("de/" if locale == DE else "")) if is_not_found else "index.html"
    en_current = ' aria-current="page"' if locale == "en" else ""
    de_current = ' aria-current="page"' if locale == DE else ""
    language_switch = (f'<nav class="language-switch" aria-label="{"Sprache wählen" if locale == DE else "Choose language"}">'
                       f'<a href="{english_link}" data-language="en" lang="en"{en_current}>English</a>'
                       f'<a href="{german_link}" data-language="de-CH" lang="de-CH"{de_current}>Deutsch</a></nav>')
    css_version = hashlib.sha256((ASSETS / "style.css").read_bytes()).hexdigest()[:12]
    js_version = hashlib.sha256((ASSETS / "site.js").read_bytes()).hexdigest()[:12]
    pagefind_assets = ""
    if page_class == "home-page":
        pagefind_assets = f'''
  <link rel="stylesheet" href="{prefix}pagefind/pagefind-component-ui.css">
  <script src="{prefix}pagefind/pagefind-component-ui.js" type="module"></script>'''
    social = social_metadata(title, description, locale, slug, image_alt) if not is_not_found else ""
    return f'''<!doctype html>
<html lang="{locale}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(description, quote=True)}">
  {social}
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
  <meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
  <meta name="theme-color" content="#f5eee2">
  <title>{html.escape(title)} · {t['site']}</title>
  <link rel="stylesheet" href="{prefix}assets/style.css?v={css_version}">{pagefind_assets}
  <script src="{prefix}assets/site.js?v={js_version}" defer></script>
</head>
<body class="{page_class}">
  <a class="skip-link" href="#main">{t['skip']}</a>
  <header class="site-header">
    <a class="wordmark" href="{home_link}" aria-label="{t['site']}, {t['all']}">
      <span class="wordmark-mark" aria-hidden="true">✦</span>
      <span>{t['site']}</span>
    </a>
    <span class="edition">{t['edition']}</span>{language_switch}
  </header>
  {content}
  <footer class="site-footer">
    <p><span aria-hidden="true">✦</span> {t['footer']}</p>
    <p class="footer-note">{t['footer_note']}</p>
  </footer>
</body>
</html>'''


def card(recipe: Recipe, index: int, locale: str = "en") -> str:
    t = UI[locale]
    tags = "".join(f'<span class="tag">{html.escape(tag_label(tag, locale))}</span>' for tag in recipe.display_tags)
    image_path = ("../" if locale == DE else "") + (recipe.image or "")
    card_image = (
        f'<img src="{html.escape(image_path, quote=True)}" alt="{html.escape(recipe.image_alt or "", quote=True)}" '
        'width="1200" height="800" loading="lazy" decoding="async" '
        'sizes="(max-width: 720px) 100vw, (max-width: 1000px) 42vw, 21vw">'
        if recipe.image else f'<span class="image-pending">{t["photo"]}</span>'
    )
    return f'''<article class="recipe-card tone-{index % 4}" data-tags="{' '.join(html.escape(t, quote=True) for t in recipe.tags)}" data-collected="{html.escape(recipe.accessed, quote=True)}">
      <a class="card-link" href="{recipe.slug}.html" aria-label="{t['open']} {html.escape(recipe.title, quote=True)}">
        <div class="card-art">
          {card_image}
          <i aria-hidden="true">0{index + 1}</i>
        </div>
        <div class="card-copy">
          <p class="card-kicker">{t['by']} {html.escape(creator_label(recipe.creator, locale))}</p>
          <h2>{html.escape(recipe.title)}</h2>
          <p class="card-meta">{recipe.ingredient_count} {t['ingredient_unit']} <span>·</span> {recipe.step_count} {t['steps']}</p>
          <div class="tag-row">{tags}</div>
          <span class="card-cta">{t['view']} <span aria-hidden="true">→</span></span>
        </div>
      </a>
    </article>'''


def build_index(recipes: list[Recipe], locale: str = "en") -> str:
    t = UI[locale]
    site_base_url = normalize_site_base_url()
    pagefind_bundle_path = f"{site_base_url}pagefind/"
    all_tags = sorted({tag for recipe in recipes for tag in recipe.display_tags})
    filters = [f'<button class="filter is-active" type="button" data-tag="all" aria-pressed="true">{t["all"]}</button>']
    filters += [f'<button class="filter" type="button" data-tag="{html.escape(tag, quote=True)}" aria-pressed="false">{html.escape(tag_label(tag, locale))}</button>' for tag in all_tags]
    newest_first = sorted(recipes, key=lambda recipe: (-int(recipe.accessed.replace("-", "")), recipe.title.casefold()))
    cards = "\n".join(card(recipe, i, locale) for i, recipe in enumerate(newest_first))
    content = f'''<main id="main">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">{t['hero_eyebrow']}</p>
          <h1>{t['hero_title']}</h1>
          <p class="hero-intro">{t['hero_intro']}</p>
        </div>
        <div class="hero-stamp" aria-hidden="true"><span>{len(recipes)}</span> {t['inside']}</div>
      </section>
      <section class="catalogue" aria-labelledby="catalogue-title">
        <div class="catalogue-head">
          <div><p class="eyebrow">{t['browse']}</p><h2 id="catalogue-title">{t['box']}</h2></div>
          <div class="search"><pagefind-config base-url="{site_base_url}" bundle-path="{pagefind_bundle_path}"></pagefind-config><pagefind-searchbox placeholder="{t['search']}" show-sub-results></pagefind-searchbox></div>
        </div>
        <div class="filters" role="group" aria-label="{t['filter']}">{''.join(filters)}</div>
        <div class="catalogue-controls">
          <p id="result-count" class="result-count" aria-live="polite" data-count-all="{t['show_all']}" data-count-one="{t['found_one']}" data-count-many="{t['found_many']}">{t['show_all'].format(n=len(recipes))}</p>
          <label class="sort-control" for="sort-recipes">{t['date']} <select id="sort-recipes"><option value="newest" selected>{t['newest']}</option><option value="oldest">{t['oldest']}</option></select></label>
        </div>
        <div class="recipe-grid" id="recipe-grid">{cards}</div>
        <div class="empty-state" id="empty-state" hidden><span aria-hidden="true">◇</span><h3>{t['empty']}</h3><p>{t['empty_hint']}</p></div>
      </section>
    </main>'''
    return shell(t['all'], t['hero_intro'], content, page_class="home-page", locale=locale, image_alt=t['site'])


def build_recipe(recipe: Recipe, locale: str = "en") -> str:
    t = UI[locale]
    ingredients = markdown_blocks(extract_section(recipe.body, "Ingredients"), "ingredients-list")
    method = markdown_blocks(extract_section(recipe.body, "Method"), "method-list")
    notes = markdown_blocks(extract_section(recipe.body, "Notes"), "notes-list")
    sources = markdown_blocks(extract_section(recipe.body, "Sources"), "sources-list")
    tags = "".join(f'<span class="tag">{html.escape(tag_label(tag, locale))}</span>' for tag in recipe.display_tags)
    image_path = ("../" if locale == DE else "") + (recipe.image or "")
    hero_image = (
        f'<figure class="recipe-hero-image"><img src="{html.escape(image_path, quote=True)}" '
        f'alt="{html.escape(recipe.image_alt or "", quote=True)}" width="1200" height="800" '
        'decoding="async" fetchpriority="high" sizes="(max-width: 720px) 100vw, 48vw"></figure>'
        if recipe.image else ''
    )
    content = f'''<main class="recipe-main" id="main">
      <nav class="breadcrumb" aria-label="{t['breadcrumb']}"><a href="index.html">{t['all']}</a><span aria-hidden="true">/</span><span>{html.escape(recipe.title)}</span></nav>
      <article class="recipe" data-pagefind-body>
        <header class="recipe-hero{' no-photo' if not recipe.image else ''}">
          <div class="recipe-hero-copy">
            <p class="eyebrow">{t['recipe']} · {t['by']} {html.escape(creator_label(recipe.creator, locale))}</p>
            <h1>{html.escape(recipe.title)}</h1>
            <div class="tag-row">{tags}</div>
            <dl class="recipe-facts">
              <div><dt>{t['ingredients']}</dt><dd>{recipe.ingredient_count}</dd></div>
              <div><dt>{t['method']}</dt><dd>{recipe.step_count} {t['steps']}</dd></div>
              <div><dt>{t['collected']}</dt><dd>{html.escape(recipe.accessed)}</dd></div>
            </dl>
          </div>
          {hero_image}
        </header>
        <div class="recipe-actions" aria-label="{t['actions']}">
          <button type="button" class="action-button" id="cook-mode"><span aria-hidden="true">◐</span> {t['cook']}</button>
          <button type="button" class="action-button" id="print-recipe"><span aria-hidden="true">⌁</span> {t['print']}</button>
          <a class="action-button" href="{html.escape(recipe.source_url, quote=True)}" rel="noopener noreferrer"><span aria-hidden="true">↗</span> {t['source']}</a>
        </div>
        <div class="recipe-layout">
          <section class="recipe-section ingredients" aria-labelledby="ingredients-heading"><p class="section-number">01</p><h2 id="ingredients-heading">{t['ingredients']}</h2>{ingredients}</section>
          <section class="recipe-section method" aria-labelledby="method-heading"><p class="section-number">02</p><h2 id="method-heading">{t['method']}</h2>{method}</section>
        </div>
        <aside class="notes" aria-labelledby="notes-heading"><div><p class="eyebrow">{t['before']}</p><h2 id="notes-heading">{t['notes']}</h2></div>{notes}</aside>
        <section class="sources" aria-labelledby="sources-heading"><p class="section-number">03</p><h2 id="sources-heading">{t['sources']}</h2>{sources}</section>
      </article>
      <div class="cook-bar" id="cook-bar" hidden><span>{t['cook']}</span><button type="button" id="exit-cook-mode">{t['exit']}</button></div>
    </main>'''
    description = f"{recipe.title}, {t['recipe'].lower()} · {t['by']} {creator_label(recipe.creator, locale)}."
    return shell(recipe.title, description, content, page_class="recipe-page", locale=locale, slug=recipe.slug,
                 image_alt=f"{recipe.title} — {recipe.image_alt}" if recipe.image_alt else recipe.title)


def build_not_found(locale: str = "en") -> str:
    t = UI[locale]
    home = normalize_site_base_url() + ("de/" if locale == DE else "")
    content = f'''<main id="main">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">404 · {t['notfound']}</p>
          <h1>{t['notfound_title']}</h1>
          <p class="hero-intro"><a href="{home}">{t['return_link']}</a>.</p>
        </div>
      </section>
    </main>'''
    return shell(t['page_title'], t['notfound_meta'], content, page_class="not-found-page", locale=locale)


def main() -> None:
    recipe_paths = sorted(ROOT.glob("*.md"))
    recipe_paths = [path for path in recipe_paths if path.name != "README.md"]
    if not recipe_paths:
        raise SystemExit("No recipe Markdown files found")
    german_recipes = load_translations(recipe_paths, ROOT / "de")
    recipes = [parse_recipe(path) for path in recipe_paths]
    recipes.sort(key=lambda recipe: recipe.title)
    german_recipes.sort(key=lambda recipe: recipe.title)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ASSETS, OUT / "assets")
    (OUT / "de").mkdir()
    (OUT / "index.html").write_text(build_index(recipes), encoding="utf-8")
    (OUT / "de" / "index.html").write_text(build_index(german_recipes, DE), encoding="utf-8")
    render_social_card(None, "en", OUT / "og" / "index.png")
    render_social_card(None, DE, OUT / "og" / "de" / "index.png")
    for recipe in recipes:
        (OUT / f"{recipe.slug}.html").write_text(build_recipe(recipe), encoding="utf-8")
        render_social_card(recipe, "en", OUT / "og" / f"{recipe.slug}.png")
    for recipe in german_recipes:
        (OUT / "de" / f"{recipe.slug}.html").write_text(build_recipe(recipe, DE), encoding="utf-8")
        render_social_card(recipe, DE, OUT / "og" / "de" / f"{recipe.slug}.png")
    (OUT / "404.html").write_text(build_not_found(), encoding="utf-8")
    (OUT / "de" / "404.html").write_text(build_not_found(DE), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "_headers").write_text(SECURITY_HEADERS, encoding="utf-8")
    print(f"Built {len(recipes)} bilingual recipes into {OUT}")
    asset_count = sum(1 for path in ASSETS.rglob("*") if path.is_file())
    print(f"Generated {2 * (len(recipes) + 2)} HTML pages and {asset_count} assets")


if __name__ == "__main__":
    main()
