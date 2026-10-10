const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function catalogue() {
  const cards = [
    ['2026-10-10', 'dessert', 'A newest'],
    ['2026-10-10', 'savoury', 'B newest'],
    ['2026-09-01', 'dessert', 'Older'],
  ].map(([collected, tags, title], index) => {
    const badge = { textContent: String(index + 1).padStart(2, '0') };
    return { dataset: { collected, tags }, hidden: false, querySelector: selector => selector === '.card-art i' ? badge : { textContent: title } };
  });
  const grid = { children: [...cards], appendChild(card) {
    this.children.splice(this.children.indexOf(card), 1);
    this.children.push(card);
  } };
  const sort = { value: 'newest', listeners: {}, addEventListener(name, callback) { this.listeners[name] = callback; } };
  const filters = ['all', 'dessert'].map(tag => ({
    dataset: { tag }, listeners: {}, classList: { toggle() {} }, setAttribute() {},
    addEventListener(name, callback) { this.listeners[name] = callback; },
  }));
  const count = { textContent: '' };
  const empty = { hidden: true };
  const document = {
    querySelectorAll(selector) { return selector === '.recipe-card' ? cards : selector === '.filter' ? filters : []; },
    querySelector(selector) { return ({ '#recipe-grid': grid, '#sort-recipes': sort, '#result-count': count, '#empty-state': empty })[selector]; },
    addEventListener() {},
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'assets', 'site.js'), 'utf8'), { document, window: {} });
  return { grid, sort, count, empty, filters };
}

test('changing date order rearranges the actual cards, with alphabetical ties', () => {
  const { grid, sort } = catalogue();
  sort.value = 'oldest';
  sort.listeners.change();
  assert.deepEqual(grid.children.map(card => card.querySelector('h2').textContent), ['Older', 'A newest', 'B newest']);
  assert.deepEqual(grid.children.map(card => card.querySelector('.card-art i').textContent), ['01', '02', '03']);
  sort.value = 'newest';
  sort.listeners.change();
  assert.deepEqual(grid.children.map(card => card.querySelector('h2').textContent), ['A newest', 'B newest', 'Older']);
});

test('sorting retains an active tag filter and its result count', () => {
  const { grid, sort, count, filters } = catalogue();
  filters[1].listeners.click();
  sort.value = 'oldest';
  sort.listeners.change();
  assert.deepEqual(grid.children.filter(card => !card.hidden).map(card => card.querySelector('h2').textContent), ['Older', 'A newest']);
  assert.equal(count.textContent, '2 recipes found');
});
