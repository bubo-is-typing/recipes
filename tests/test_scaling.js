const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const { parseHTML } = require('linkedom');
const script = fs.readFileSync('assets/site.js', 'utf8');

function recipePage({slug='epicurious-fluffy-pancakes', locale='en', storage=new Map(), blocked=false, run=true, ingredients=null} = {}) {
  const html = execFileSync('python3', ['-c', `import build; from pathlib import Path; recipe = build.parse_recipe(Path(${JSON.stringify((locale === 'en' ? '' : 'de/') + slug + '.md')})); ingredients = ${ingredients === null ? 'None' : JSON.stringify(ingredients)}; recipe.body = recipe.body if ingredients is None else recipe.body.replace(build.extract_section(recipe.body, 'Ingredients'), ingredients); print(build.build_recipe(recipe, ${JSON.stringify(locale)}))`], {encoding:'utf8'});
  const {document, window} = parseHTML(html);
  document.cookie = '';
  Object.assign(window, {location: {href:`https://example.test/${slug}`, pathname:`/${slug}`, assign(){}}, scrollTo(){}, print(){}});
  Object.defineProperty(window, 'sessionStorage', {configurable:true, value: {
    getItem(key) { if (blocked) throw Error('blocked'); return storage.get(key) ?? null; },
    setItem(key, value) { if (blocked) throw Error('blocked'); storage.set(key, value); },
  }});
  if (run) vm.runInNewContext(script, {document, window, URL, navigator:{language:locale}});
  const get = selector => document.querySelector(selector);
  const change = (selector, value) => { const node=get(selector); node.value=String(value); node.dispatchEvent(new window.Event('input')); };
  const click = selector => get(selector).dispatchEvent(new window.Event('click'));
  return {document, window, get, change, click, storage};
}

test('actual EN/DE oats scale optional total weights along with spoon amounts', () => {
  for (const locale of ['en', 'de-CH']) {
    const page = recipePage({slug:'date-caramel-blended-oats', locale});
    const item = [...page.document.querySelectorAll('.ingredients-list li')].find(node => node.textContent.includes(locale === 'en' ? 'almond butter' : 'Mandelmus'));
    const baseline = item.innerHTML;
    page.change('#scale-factor', 2);
    assert.equal(item.textContent, locale === 'en' ? '4 tbsp almond butter (about 90 g; optional)' : '4 EL Mandelmus (etwa 90 g; optional)');
    page.click('#scale-reset');
    assert.equal(item.innerHTML, baseline);
  }
});

test('actual EN/DE brownie batter leaves explicitly unspecified units entirely unscaled', () => {
  for (const locale of ['en', 'de-CH']) {
    const page = recipePage({slug:'greek-yogurt-brownie-batter', locale});
    const item = [...page.document.querySelectorAll('.ingredients-list li')].find(node => node.textContent.includes(locale === 'en' ? 'unit not specified' : 'Einheit von der Urheberin nicht angegeben'));
    const baseline = item.innerHTML;
    page.change('#scale-factor', 2);
    assert.equal(item.innerHTML, baseline);
    assert.equal(item.querySelectorAll('[data-quantity]').length, 0);
    assert.equal(item.textContent, locale === 'en' ? '30–40 milk or water (unit not specified by the creator)' : '30–40 Milch oder Wasser (Einheit von der Urheberin nicht angegeben)');
    assert.ok([...page.document.querySelectorAll('.ingredients-list [data-quantity]')].some(node => Number(node.textContent.replace(',', '.')) === Number(node.dataset.quantity) * 2));
  }
});

test('space-separated Unicode mixed fractions scale complete tokens and normalize cups', () => {
  for (const locale of ['en', 'de-CH']) {
    const page = recipePage({locale, ingredients:'- 1 ½ tsp salt\n- 1 ⅔ cups flour\n- 1 ⅔–2 cups oats'});
    const items = [...page.document.querySelectorAll('.ingredients-list li')];
    const baseline = items.map(item => item.innerHTML);
    assert.equal(items[0].textContent, '1 ½ tsp salt');
    assert.equal(items[0].querySelector('[data-quantity]').dataset.quantity, '1.5');
    assert.equal(items[1].textContent, '≈ 400 ml flour');
    assert.equal(items[1].querySelector('[data-quantity]').dataset.quantity, '400');
    page.change('#scale-factor', 2);
    assert.equal(items[0].textContent, '3 tsp salt');
    assert.equal(items[1].textContent, '≈ 800 ml flour');
    assert.equal(items[2].textContent, locale === 'en' ? '3.33333–4 cups oats' : '3,33333–4 cups oats');
    page.click('#scale-reset');
    assert.deepEqual(items.map(item => item.innerHTML), baseline);
  }
});

test('slider scales actual rendered fractions, eggs and reset restores exact baseline without drift', () => {
  const page = recipePage();
  const baseline=page.get('.ingredients-list').textContent;
  assert.equal(page.get('#scale-controls').hidden, false);
  assert.equal(page.get('#scale-slider').getAttribute('min'), '0.25');
  assert.equal(page.get('#scale-slider').getAttribute('max'), '4');
  assert.equal(page.get('#scale-slider').getAttribute('step'), '0.25');
  page.change('#scale-slider', 0.5);
  assert.match(page.get('.ingredients-list').textContent, /0\.75 tsp salt/);
  assert.match(page.get('.ingredients-list').textContent, /1\.5 eggs/);
  assert.match(page.get('#scale-status').textContent, /0\.5×/);
  for (let i=0;i<50;i++) { page.change('#scale-factor', 3); page.change('#scale-factor', 0.5); }
  assert.match(page.get('.ingredients-list').textContent, /0\.75 tsp salt/);
  page.click('#scale-reset');
  assert.equal(page.get('.ingredients-list').textContent, baseline);
  assert.equal(page.get('#scale-factor').value, '1');
});

test('custom factors validate accessibly; German decimals, small quantities and zero ranges remain meaningful', () => {
  const page = recipePage({slug:'home-oven-pepperoni-pizza', locale:'de-CH'});
  page.change('#scale-factor', 0.1);
  assert.match(page.get('.ingredients-list').textContent, /0,11 g aktive Trockenhefe/);
  assert.match(page.get('.ingredients-list').textContent, /0,1 Dose à 794 g/);
  const scaled = page.get('.ingredients-list').textContent;
  for (const invalid of ['', '-1', '0', '0.09', '20.01', 'NaN', 'Infinity']) {
    page.change('#scale-factor', invalid);
    assert.equal(page.get('.ingredients-list').textContent, scaled);
    assert.equal(page.get('#scale-factor').getAttribute('aria-invalid'), 'true');
  }
  page.change('#scale-factor', 20);
  assert.equal(page.get('#scale-factor').getAttribute('aria-invalid'), 'false');
  page.change('#scale-factor', 1.37);
  assert.equal(page.get('#scale-factor').value, '1.37');
  const ranges = recipePage({slug:'chocolate-biscoff-protein-bowl'});
  ranges.change('#scale-factor', 0.1);
  assert.match(ranges.get('.ingredients-list').textContent, /0–6 ml/);
  assert.match(ranges.get('.ingredients-list').textContent, /0\.3–0\.4 g/);
});

test('method stays original with visible warning in cook and print; no-JS remains usable and controls hidden', () => {
  for (const locale of ['en', 'de-CH']) {
    const page = recipePage({slug:'home-oven-pepperoni-pizza', locale});
    const method = page.get('.method-list').innerHTML;
    const sources = page.get('.source-measurements').innerHTML;
    page.change('#scale-factor', 2);
    assert.equal(page.get('.method-list').innerHTML, method);
    assert.equal(page.get('.source-measurements').innerHTML, sources);
    assert.ok(page.get('#scale-note').textContent.includes(locale === 'en' ? 'eggs' : 'Eier'));
    assert.ok(page.get('#method-scale-note').textContent.toLowerCase().includes('original'));
    page.click('#cook-mode');
    assert.equal(page.document.body.classList.contains('cook-mode'), true);
    assert.ok(page.get('#method-scale-note').closest('.method'));
    page.click('#exit-cook-mode');
    assert.equal(page.document.body.classList.contains('cook-mode'), false);
    const nojs = recipePage({locale, run:false});
    assert.equal(nojs.get('#scale-controls').hidden, true);
    assert.match(nojs.get('.ingredients-list').textContent, /1½/);
    assert.equal(nojs.get('#scale-status').textContent.startsWith('1×'), true);
  }
  const css = fs.readFileSync('assets/style.css', 'utf8');
  const print = css.slice(css.indexOf('@media print'));
  assert.match(print, /#scale-controls[^}]*display:\s*none/);
  assert.doesNotMatch(print, /#(?:scale-note|method-scale-note|scale-status)[^}]*display:\s*none/);
});

test('numeric editing does not rewrite valid input mid-keystroke', () => {
  const page = recipePage();
  page.change('#scale-factor', '2.');
  assert.equal(page.get('#scale-factor').value, '2.');
  page.change('#scale-factor', '2.50');
  assert.equal(page.get('#scale-factor').value, '2.50');
  assert.match(page.get('#scale-status').textContent, /2\.5×/);
});

test('every EN/DE recipe scales structured baselines and resets byte-exactly at both site bases', () => {
  for (const base of ['/', '/recipes/']) {
    const pages = JSON.parse(execFileSync('python3', ['-c', `import build,json; from pathlib import Path; print(json.dumps([build.build_recipe(build.parse_recipe(p), locale) for locale, folder in [('en', Path('.')), ('de-CH', Path('de'))] for p in sorted(folder.glob('*.md')) if p.name != 'README.md']))`], {encoding:'utf8', env:{...process.env, SITE_BASE_URL:base}}));
    assert.ok(pages.length > 60);
    for (const html of pages) {
      const {document, window} = parseHTML(html);
      document.cookie = '';
      Object.assign(window, {location:{pathname:base, href:'https://example.test'+base, assign(){}}});
      Object.defineProperty(window, 'sessionStorage', {configurable:true, value:{getItem(){return null;},setItem(){}}});
      const before = document.querySelector('.ingredients-list').innerHTML;
      const method = document.querySelector('.method-list').innerHTML;
      const numbers = [...document.querySelectorAll('.ingredients-list [data-quantity]')];
      assert.ok(numbers.length > 0);
      vm.runInNewContext(script, {document, window, URL, navigator:{language:'en'}});
      const input = document.querySelector('#scale-factor');
      input.value='2'; input.dispatchEvent(new window.Event('input'));
      for (const number of numbers) {
        const value = Number(number.textContent.replace(',', '.'));
        assert.ok(Math.abs(value-Number(number.dataset.quantity)*2) < 0.00001);
      }
      assert.equal(document.querySelector('.method-list').innerHTML, method);
      document.querySelector('#scale-reset').dispatchEvent(new window.Event('click'));
      assert.equal(document.querySelector('.ingredients-list').innerHTML, before);
    }
    console.log(`Verified ${pages.length} recipe DOMs at ${base}`);
  }
});

test('session factor survives language navigation only for same recipe; storage failures are harmless', () => {
  const storage = new Map();
  const en = recipePage({storage});
  en.change('#scale-factor', 2.5);
  const de = recipePage({storage, locale:'de-CH'});
  assert.equal(de.get('#scale-factor').value, '2.5');
  assert.match(de.get('#scale-status').textContent, /2,5×/);
  assert.equal(recipePage({storage, slug:'whole-lime-loaf-cake'}).get('#scale-factor').value, '1');
  de.click('#scale-reset');
  assert.equal(recipePage({storage}).get('#scale-factor').value, '1');
  const blocked = recipePage({blocked:true});
  blocked.change('#scale-factor', 2);
  assert.match(blocked.get('.ingredients-list').textContent, /6 eggs/);
  assert.equal(blocked.get('#scale-controls').hidden, false);
  for (const bad of ['0', 'Infinity', '-1', '21', 'oops']) {
    storage.set('recipe-scale:epicurious-fluffy-pancakes', bad);
    assert.equal(recipePage({storage}).get('#scale-factor').value, '1');
  }
});
