const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = path.join(__dirname, '..');
const read = file => fs.readFileSync(path.join(base,file),'utf8');

test('página pública apresenta cadastro sem perguntas, respostas ou formulários de exercício',()=>{
  const html=read('web/index.html');
  assert.match(html,/Cadastro gratuito/);
  assert.match(html,/href="\/estudar"/);
  assert.doesNotMatch(html,/id="(?:question-form|rewrite-form)"|type="radio"|<textarea|R\$ 170/);
});

test('conteúdo de questões e antigo gabarito demonstrativo não ficam na raiz estática',()=>{
  assert.equal(fs.existsSync(path.join(base,'web/learning-library.json')),false);
  assert.equal(fs.existsSync(path.join(base,'web/essay-fixture.js')),false);
  const data=JSON.parse(read('data/learning-library.json'));
  assert.equal(data.tracks.reduce((n,t)=>n+t.lessons.length,0),18);
  assert.doesNotMatch(read('web/app.js'),/MOIRAE_ANNOTATIONS|FormData|resposta correta|R\$ 170/);
});

test('biblioteca consulta API autenticada e limpa o conteúdo ao sair da página',()=>{
  const script=read('web/learning-library.js');
  assert.match(script,/fetch\('\/api\/learning-library'/);
  assert.doesNotMatch(script,/fetch\(['"]learning-library\.json/);
  assert.match(script,/response\.status===401\|\|response\.status===403/);
  assert.match(script,/pagehide/);
  assert.match(script,/progress_key/);
  assert.doesNotMatch(script,/innerHTML/);
});
