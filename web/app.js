'use strict';
const form = document.querySelector('#question-form');
const feedback = document.querySelector('#feedback');
const reset = form.querySelector('[type="reset"]');
form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const correct = new FormData(form).get('answer') === 'b';
  feedback.textContent = (correct ? 'Você acertou! ' : 'A resposta correta é R$ 170. ') + '15% de R$ 200 = 0,15 × 200 = R$ 30. Subtraindo o desconto: 200 − 30 = R$ 170. Demonstração concluída; nenhuma resposta foi salva.';
  feedback.hidden = false;
  form.querySelector('fieldset').disabled = true;
  form.querySelector('[type="submit"]').hidden = true;
  reset.hidden = false;
  feedback.focus();
});
form.addEventListener('reset', () => {
  form.querySelector('fieldset').disabled = false;
  feedback.hidden = true;
  feedback.textContent = '';
  reset.hidden = true;
  form.querySelector('[type="submit"]').hidden = false;
  form.querySelector('input').focus();
});

// Demos locais: não representam personalização nem avaliação por IA.
const durations = {15: ['2 questões', 'Porcentagem', 'Uma resolução comentada'], 30: ['3 questões', 'Porcentagem', 'Resoluções comentadas'], 60: ['5 questões', 'Porcentagem e proporção', 'Resoluções comentadas']};
document.querySelectorAll('[data-minutes]').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('[data-minutes]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    const labels = ['Aquecer', 'Praticar', 'Revisar'];
    document.querySelectorAll('#session-preview p').forEach((row, index) => {
      const title = document.createElement('strong'); title.textContent = labels[index];
      row.replaceChildren(title, document.createTextNode(' · ' + durations[button.dataset.minutes][index]));
    });
  });
});
const annotations = MOIRAE_ANNOTATIONS;
let selectedAnnotation = 'argument';
const rewriteForm = document.querySelector('#rewrite-form');
const rewriteInput = document.querySelector('#rewrite');
const rewriteResult = document.querySelector('#rewrite-result');
const drafts = new Map();
document.querySelectorAll('[data-annotation]').forEach(button => {
  button.addEventListener('click', () => {
    drafts.set(selectedAnnotation, rewriteInput.value);
    selectedAnnotation = button.dataset.annotation;
    const annotation = annotations[selectedAnnotation];
    document.querySelectorAll('[data-annotation]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    document.querySelector('#annotation-title').textContent = annotation.title;
    document.querySelector('#annotation-explanation').textContent = annotation.explanation;
    document.querySelector('#annotation-question').textContent = 'Pergunta para revisar: ' + annotation.question;
    rewriteInput.value = drafts.get(selectedAnnotation) || '';
    rewriteResult.hidden = true;
  });
});
rewriteForm.addEventListener('submit', event => {
  event.preventDefault();
  rewriteInput.setCustomValidity(rewriteInput.value.trim().length < 20 ? 'Escreva pelo menos 20 caracteres, além de espaços.' : '');
  if (!rewriteForm.reportValidity()) return;
  drafts.set(selectedAnnotation, rewriteInput.value);
  document.querySelector('#rewrite-before').textContent = annotations[selectedAnnotation].original;
  document.querySelector('#rewrite-after').textContent = rewriteInput.value.trim();
  rewriteResult.hidden = false;
});
rewriteInput.addEventListener('input', () => { rewriteInput.setCustomValidity(''); rewriteResult.hidden = true; });
rewriteForm.addEventListener('reset', () => {
  drafts.delete(selectedAnnotation); rewriteInput.setCustomValidity(''); rewriteResult.hidden = true;
});
