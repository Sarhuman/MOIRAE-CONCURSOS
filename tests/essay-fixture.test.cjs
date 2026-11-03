const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const base = path.join(__dirname, '..', 'web');
const fixtures = vm.runInNewContext(fs.readFileSync(path.join(base, 'essay-fixture.js'), 'utf8') + '\nMOIRAE_ANNOTATIONS');
test('três comentários completos disponíveis sem API', () => {
  assert.deepEqual(Object.keys(fixtures).sort(), ['argument', 'cohesion', 'intervention']);
  for (const item of Object.values(fixtures)) {
    for (const key of ['title', 'explanation', 'question', 'original']) assert.ok(item[key].trim());
  }
});
test('trechos das fixtures correspondem ao exemplo exibido', () => {
  const html = fs.readFileSync(path.join(base, 'index.html'), 'utf8');
  for (const item of Object.values(fixtures)) assert.ok(html.includes(item.original));
});
test('fixture carrega antes do consumidor e reescrita usa saída textual', () => {
  const html = fs.readFileSync(path.join(base, 'index.html'), 'utf8');
  assert.ok(html.indexOf('essay-fixture.js') < html.indexOf('app.js'));
  const app = fs.readFileSync(path.join(base, 'app.js'), 'utf8');
  assert.match(app, /const annotations = MOIRAE_ANNOTATIONS/);
  assert.match(app, /querySelector\('#rewrite-after'\)\.textContent/);
  assert.doesNotMatch(app, /innerHTML/);
});
