(() => {
  const cards = [...document.querySelectorAll('.recipe-card')];
  const filters = [...document.querySelectorAll('.filter')];
  const count = document.querySelector('#result-count');
  const empty = document.querySelector('#empty-state');
  let activeTag = 'all';

  const applyFilters = () => {
    let visible = 0;
    cards.forEach((card) => {
      const show = activeTag === 'all' || card.dataset.tags.split(' ').includes(activeTag);
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (count) count.textContent = activeTag === 'all'
      ? `Showing all ${visible} recipes`
      : `${visible} recipe${visible === 1 ? '' : 's'} found`;
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
