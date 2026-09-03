#!/usr/bin/env python3
"""Build the recipe collection into a dependency-free static site."""

from __future__ import annotations

import html
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
ASSETS = ROOT / "assets"
DEFAULT_SITE_BASE_URL = "/recipes/"
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


@dataclass
class Recipe:
    slug: str
    title: str
    creator: str
    source_url: str
    accessed: str
    tags: list[str]
    image: str
    image_alt: str
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
    required = ("title", "source_creator", "source_url", "accessed", "tags", "image", "image_alt")
    missing = [key for key in required if key not in meta]
    if missing:
        raise ValueError(f"{path.name}: missing frontmatter: {', '.join(missing)}")
    return Recipe(
        slug=path.stem,
        title=str(meta["title"]),
        creator=str(meta["source_creator"]),
        source_url=str(meta["source_url"]),
        accessed=str(meta["accessed"]),
        tags=list(meta["tags"]),
        image=str(meta["image"]),
        image_alt=str(meta["image_alt"]),
        body=body.strip(),
    )


def extract_section(markdown: str, name: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", markdown)
    return match.group(1).strip() if match else ""


def inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
    return pattern.sub(
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" rel="noopener noreferrer">{m.group(1)}</a>',
        escaped,
    )


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


def shell(title: str, description: str, content: str, *, page_class: str = "") -> str:
    pagefind_assets = ""
    if page_class == "home-page":
        pagefind_assets = '''
  <link rel="stylesheet" href="pagefind/pagefind-component-ui.css">
  <script src="pagefind/pagefind-component-ui.js" type="module"></script>'''
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
  <meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
  <meta name="theme-color" content="#f5eee2">
  <title>{html.escape(title)} · The Recipe Index</title>
  <link rel="stylesheet" href="assets/style.css">{pagefind_assets}
  <script src="assets/site.js" defer></script>
</head>
<body class="{page_class}">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <a class="wordmark" href="index.html" aria-label="The Recipe Index, home">
      <span class="wordmark-mark" aria-hidden="true">✦</span>
      <span>The Recipe Index</span>
    </a>
    <span class="edition">A small-batch recipe journal</span>
  </header>
  {content}
  <footer class="site-footer">
    <p><span aria-hidden="true">✦</span> Collected with care, cooked with curiosity.</p>
    <p class="footer-note">Recipes retain their original creator attribution and sources.</p>
  </footer>
</body>
</html>'''


def card(recipe: Recipe, index: int) -> str:
    tags = "".join(f'<span class="tag">{html.escape(tag.replace("-", " "))}</span>' for tag in recipe.display_tags)
    return f'''<article class="recipe-card tone-{index % 4}" data-tags="{' '.join(html.escape(t, quote=True) for t in recipe.tags)}">
      <a class="card-link" href="{recipe.slug}.html" aria-label="Open {html.escape(recipe.title, quote=True)}">
        <div class="card-art">
          <img src="{html.escape(recipe.image, quote=True)}" alt="{html.escape(recipe.image_alt, quote=True)}" width="1200" height="800" loading="lazy" decoding="async" sizes="(max-width: 720px) 100vw, (max-width: 1000px) 42vw, 21vw">
          <i aria-hidden="true">0{index + 1}</i>
        </div>
        <div class="card-copy">
          <p class="card-kicker">By {html.escape(recipe.creator)}</p>
          <h2>{html.escape(recipe.title)}</h2>
          <p class="card-meta">{recipe.ingredient_count} ingredients <span>·</span> {recipe.step_count} steps</p>
          <div class="tag-row">{tags}</div>
          <span class="card-cta">View recipe <span aria-hidden="true">→</span></span>
        </div>
      </a>
    </article>'''


def build_index(recipes: list[Recipe]) -> str:
    site_base_url = normalize_site_base_url()
    pagefind_bundle_path = f"{site_base_url}pagefind/"
    all_tags = sorted({tag for recipe in recipes for tag in recipe.display_tags})
    filters = ['<button class="filter is-active" type="button" data-tag="all" aria-pressed="true">All recipes</button>']
    filters += [f'<button class="filter" type="button" data-tag="{html.escape(tag, quote=True)}" aria-pressed="false">{html.escape(tag.replace("-", " "))}</button>' for tag in all_tags]
    cards = "\n".join(card(recipe, i) for i, recipe in enumerate(recipes))
    content = f'''<main id="main">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">Volume 01 · Something good</p>
          <h1>Recipes worth<br><em>making again.</em></h1>
          <p class="hero-intro">A considered collection of recipes worth keeping—sourced carefully and ready for the kitchen.</p>
        </div>
        <div class="hero-stamp" aria-hidden="true"><span>{len(recipes)}</span> recipes<br>inside</div>
      </section>
      <section class="catalogue" aria-labelledby="catalogue-title">
        <div class="catalogue-head">
          <div><p class="eyebrow">Browse the collection</p><h2 id="catalogue-title">The recipe box</h2></div>
          <div class="search"><pagefind-config base-url="{site_base_url}" bundle-path="{pagefind_bundle_path}"></pagefind-config><pagefind-searchbox placeholder="Search recipes and ingredients…" show-sub-results></pagefind-searchbox></div>
        </div>
        <div class="filters" role="group" aria-label="Filter recipes by tag">{''.join(filters)}</div>
        <p id="result-count" class="result-count" aria-live="polite">Showing all {len(recipes)} recipes</p>
        <div class="recipe-grid" id="recipe-grid">{cards}</div>
        <div class="empty-state" id="empty-state" hidden><span aria-hidden="true">◇</span><h3>No recipes found</h3><p>Try another word or clear the selected filter.</p></div>
      </section>
    </main>'''
    return shell("Recipes", "A small collection of carefully sourced recipes.", content, page_class="home-page")


def build_recipe(recipe: Recipe) -> str:
    ingredients = markdown_blocks(extract_section(recipe.body, "Ingredients"), "ingredients-list")
    method = markdown_blocks(extract_section(recipe.body, "Method"), "method-list")
    notes = markdown_blocks(extract_section(recipe.body, "Notes"), "notes-list")
    sources = markdown_blocks(extract_section(recipe.body, "Sources"), "sources-list")
    tags = "".join(f'<span class="tag">{html.escape(tag.replace("-", " "))}</span>' for tag in recipe.display_tags)
    content = f'''<main class="recipe-main" id="main">
      <nav class="breadcrumb" aria-label="Breadcrumb"><a href="index.html">All recipes</a><span aria-hidden="true">/</span><span>{html.escape(recipe.title)}</span></nav>
      <article class="recipe" data-pagefind-body>
        <header class="recipe-hero">
          <div class="recipe-hero-copy">
            <p class="eyebrow">Recipe · By {html.escape(recipe.creator)}</p>
            <h1>{html.escape(recipe.title)}</h1>
            <div class="tag-row">{tags}</div>
            <dl class="recipe-facts">
              <div><dt>Ingredients</dt><dd>{recipe.ingredient_count}</dd></div>
              <div><dt>Method</dt><dd>{recipe.step_count} steps</dd></div>
              <div><dt>Collected</dt><dd>{html.escape(recipe.accessed)}</dd></div>
            </dl>
          </div>
          <figure class="recipe-hero-image">
            <img src="{html.escape(recipe.image, quote=True)}" alt="{html.escape(recipe.image_alt, quote=True)}" width="1200" height="800" decoding="async" fetchpriority="high" sizes="(max-width: 720px) 100vw, 48vw">
          </figure>
        </header>
        <div class="recipe-actions" aria-label="Recipe actions">
          <button type="button" class="action-button" id="cook-mode"><span aria-hidden="true">◐</span> Cooking mode</button>
          <button type="button" class="action-button" id="print-recipe"><span aria-hidden="true">⌁</span> Print recipe</button>
          <a class="action-button" href="{html.escape(recipe.source_url, quote=True)}" rel="noopener noreferrer"><span aria-hidden="true">↗</span> Original source</a>
        </div>
        <div class="recipe-layout">
          <section class="recipe-section ingredients" aria-labelledby="ingredients-heading"><p class="section-number">01</p><h2 id="ingredients-heading">Ingredients</h2>{ingredients}</section>
          <section class="recipe-section method" aria-labelledby="method-heading"><p class="section-number">02</p><h2 id="method-heading">Method</h2>{method}</section>
        </div>
        <aside class="notes" aria-labelledby="notes-heading"><div><p class="eyebrow">Before you begin</p><h2 id="notes-heading">Cook’s notes</h2></div>{notes}</aside>
        <section class="sources" aria-labelledby="sources-heading"><p class="section-number">03</p><h2 id="sources-heading">Sources & attribution</h2>{sources}</section>
      </article>
      <div class="cook-bar" id="cook-bar" hidden><span>Cooking mode</span><button type="button" id="exit-cook-mode">Exit</button></div>
    </main>'''
    return shell(recipe.title, f"{recipe.title}, a recipe by {recipe.creator}.", content, page_class="recipe-page")


def build_not_found() -> str:
    content = '''<main id="main">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">404 · Not found</p>
          <h1>This page is<br><em>off the menu.</em></h1>
          <p class="hero-intro"><a href="/recipes/">Return to the recipe index</a>.</p>
        </div>
      </section>
    </main>'''
    return shell("Page not found", "The requested recipe page was not found.", content)


def main() -> None:
    recipe_paths = sorted(ROOT.glob("*.md"))
    recipe_paths = [path for path in recipe_paths if path.name != "README.md"]
    if not recipe_paths:
        raise SystemExit("No recipe Markdown files found")
    recipes = [parse_recipe(path) for path in recipe_paths]
    recipes.sort(key=lambda recipe: recipe.title)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ASSETS, OUT / "assets")
    (OUT / "index.html").write_text(build_index(recipes), encoding="utf-8")
    for recipe in recipes:
        (OUT / f"{recipe.slug}.html").write_text(build_recipe(recipe), encoding="utf-8")
    (OUT / "404.html").write_text(build_not_found(), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "_headers").write_text(SECURITY_HEADERS, encoding="utf-8")
    print(f"Built {len(recipes)} recipes into {OUT}")
    asset_count = sum(1 for path in ASSETS.rglob("*") if path.is_file())
    print(f"Generated {len(recipes) + 2} HTML pages and {asset_count} assets")


if __name__ == "__main__":
    main()
