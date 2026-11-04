'use strict';
// Visual demonstration only. This module cannot issue coupons or change checkout prices.
(() => {
  const open = document.querySelector('#coupon-open');
  const dialog = document.querySelector('#coupon-dialog');
  if (!open || !dialog || typeof dialog.showModal !== 'function') return;
  const spin = document.querySelector('#coupon-spin');
  const wheel = document.querySelector('#coupon-wheel');
  const result = document.querySelector('#coupon-result');
  let rotation = 0;
  open.hidden = false;
  open.addEventListener('click', () => dialog.showModal());
  document.querySelector('#coupon-close').addEventListener('click', () => dialog.close());
  document.querySelector('#coupon-plans').addEventListener('click', () => dialog.close());
  spin.addEventListener('click', () => {
    if (spin.disabled) return;
    spin.disabled = true;
    result.textContent = 'Giro demonstrativo em andamento…';
    rotation += 1800 + Math.floor(Math.random() * 360);
    wheel.style.transform = `rotate(${rotation}deg)`;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.setTimeout(() => {
      result.textContent = 'Demonstração concluída. Nenhum cupom foi emitido e nenhum preço foi alterado. Explore os planos enquanto preparamos a campanha.';
      spin.textContent = 'Testar novamente';
      spin.disabled = false;
    }, reduced ? 0 : 1850);
  });
})();
