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
