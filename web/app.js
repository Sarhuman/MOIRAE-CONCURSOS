'use strict';
// Prévia de organização do estudo. Perguntas e exercícios exigem conta.
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
