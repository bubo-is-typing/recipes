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
