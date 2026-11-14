(() => {
  // Only explicit language choices set a cookie; direct German links stay put.
  const languageLinks = [...document.querySelectorAll('[data-language]')];
  languageLinks.forEach((link) => link.addEventListener('click', () => {
    document.cookie = `lang=${link.dataset.language}; Path=/; SameSite=Lax; Max-Age=31536000`;
  }));
  if (languageLinks.length && typeof window !== 'undefined' && window.location &&
      document.documentElement?.lang === 'en' && !window.location.pathname.endsWith('/404.html')) {
    const choice = document.cookie.match(/(?:^|;\s*)lang=(en|de-CH)(?:;|$)/)?.[1];
    const preferred = typeof navigator !== 'undefined' ?
      (navigator.languages?.[0] || navigator.language || '') : '';
    if (choice === 'de-CH' || (!choice && /^de(?:-|$)/i.test(preferred))) {
      const targetLink = languageLinks.find(link => link.dataset.language === 'de-CH');
      if (targetLink) {
        const target = new URL(targetLink.getAttribute('href'), window.location.href);
        if (target.pathname !== window.location.pathname) window.location.assign(target.href);
      }
    }
  }

  const cards = [...document.querySelectorAll('.recipe-card')];
  const filters = [...document.querySelectorAll('.filter')];
  const count = document.querySelector('#result-count');
  const empty = document.querySelector('#empty-state');
  const sort = document.querySelector('#sort-recipes');
  const grid = document.querySelector('#recipe-grid');
  let activeTag = 'all';

  sort?.addEventListener('change', () => {
    const direction = sort.value === 'oldest' ? 1 : -1;
    const ordered = [...cards].sort((a, b) => direction * a.dataset.collected.localeCompare(b.dataset.collected));
    ordered.forEach((card, index) => {
      grid.appendChild(card);
      const badge = card.querySelector('.card-art i');
      if (badge) badge.textContent = String(index + 1).padStart(2, '0');
    });
  });

  const applyFilters = () => {
    let visible = 0;
    cards.forEach((card) => {
      const show = activeTag === 'all' || card.dataset.tags.split(' ').includes(activeTag);
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (count) {
      const templates = count.dataset || {};
      const template = activeTag === 'all'
        ? (templates.countAll || 'Showing all {n} recipes')
        : visible === 1 ? (templates.countOne || '{n} recipe found') : (templates.countMany || '{n} recipes found');
      count.textContent = template.replace('{n}', String(visible));
    }
    if (empty) empty.hidden = visible !== 0;
  };

  filters.forEach((filter) => filter.addEventListener('click', () => {
    activeTag = filter.dataset.tag;
    filters.forEach((item) => {
      const selected = item === filter;
      item.classList.toggle('is-active', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    applyFilters();
  }));

  const scale = document.querySelector('#recipe-scale');
  if (scale) {
    const factorInput = document.querySelector('#scale-factor');
    const slider = document.querySelector('#scale-slider');
    const status = document.querySelector('#scale-status');
    const storageKey = `recipe-scale:${scale.dataset.recipeSlug}`;
    const quantities = [...document.querySelectorAll('.ingredients-list [data-quantity]')]
      .map(node => ({ node, value: Number(node.dataset.quantity), original: node.textContent }));
    // German recipe prose uses decimal commas (including our de-CH edition).
    const numberLocale = document.documentElement.lang === 'de-CH' ? 'de-DE' : 'en';
    const format = value => new Intl.NumberFormat(numberLocale, { maximumSignificantDigits: 6, useGrouping: false }).format(value);
    const applyScale = (value, editing = false) => {
      const factor = Number(value);
      const valid = Number.isFinite(factor) && factor >= 0.1 && factor <= 20;
      factorInput.setAttribute('aria-invalid', String(!valid));
      if (!valid) return;
      quantities.forEach(({ node, value: baseline, original }) => {
        node.textContent = factor === 1 ? original : format(baseline * factor);
      });
      // Do not erase a trailing decimal point or move the caret while typing.
      if (!editing) factorInput.value = String(factor);
      slider.value = String(Math.max(0.25, Math.min(4, factor)));
      status.textContent = `${format(factor)}× · ${status.dataset.original}`;
      try { window.sessionStorage.setItem(storageKey, String(factor)); } catch { /* Private/blocked storage: scaling still works. */ }
    };
    slider.addEventListener('input', () => applyScale(slider.value));
    factorInput.addEventListener('input', () => applyScale(factorInput.value, true));
    document.querySelector('#scale-reset').addEventListener('click', () => applyScale(1));
    let initial = 1;
    try {
      const stored = Number(window.sessionStorage.getItem(storageKey));
      if (Number.isFinite(stored) && stored >= 0.1 && stored <= 20) initial = stored;
    } catch { /* Storage is optional. */ }
    applyScale(initial);
    document.querySelector('#scale-controls').hidden = false;
  }

  document.querySelector('#print-recipe')?.addEventListener('click', () => window.print());

  const setCookMode = (enabled) => {
    document.body.classList.toggle('cook-mode', enabled);
    const bar = document.querySelector('#cook-bar');
    if (bar) bar.hidden = !enabled;
    if (enabled) window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  document.querySelector('#cook-mode')?.addEventListener('click', () => setCookMode(true));
  document.querySelector('#exit-cook-mode')?.addEventListener('click', () => setCookMode(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && document.body.classList.contains('cook-mode')) setCookMode(false);
  });
})();
