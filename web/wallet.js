'use strict';
(() => {
  const $ = s => document.querySelector(s);
  const status = $('#wallet-status');
  const kinds = {grant:'Créditos de teste recebidos',reserve:'Crédito reservado',consume:'Crédito consumido',release:'Reserva liberada',refund:'Crédito estornado',revoke:'Lote revogado'};
  const states = {active:'Ativo',expired:'Vencido',revoked:'Revogado'};
  const date = n => new Date(n*1000).toLocaleString('pt-BR');
  const node = (tag,text) => { const e=document.createElement(tag);e.textContent=text;return e; };
  let busy=false;
  async function refresh() {
    if(busy)return;
    busy=true;$('#wallet-refresh').disabled=true;status.textContent='Consultando sua carteira…';
    try {
      const r=await fetch('/api/sandbox/wallet',{credentials:'same-origin',cache:'no-store'});
      const data=await r.json();
      if(!r.ok){
        $('#wallet-content').hidden=true;$('#wallet-help').hidden=false;
        $('#wallet-help-text').textContent=r.status===401?'Entre na sua conta de teste para consultar os créditos.':data.detail||'A carteira não está disponível neste ambiente.';
        status.textContent=r.status===503?'Carteira sandbox desativada. Nenhum saldo real foi alterado.':'Não foi possível consultar a carteira.';return;
      }
      $('#wallet-help').hidden=true;$('#wallet-content').hidden=false;
      $('#wallet-available').textContent=String(data.available);
      $('#wallet-reserved').textContent=String(data.lots.reduce((n,l)=>n+l.reserved,0));
      $('#wallet-consumed').textContent=String(data.lots.reduce((n,l)=>n+l.consumed,0));
      $('#wallet-notice').textContent=data.notice;
      $('#wallet-lots').replaceChildren(...data.lots.map(l=>{
        const card=document.createElement('article');card.className='wallet-lot';
        card.append(node('h3',`${l.units} créditos · ${states[l.status]||'Indisponível'}`),node('p',`Validade: ${date(l.expires_at)}`),node('p',`Saldo do lote: ${l.available} · Reservados: ${l.reserved} · Consumidos: ${l.consumed}`),node('p',l.status==='active'?'Saldo disponível apenas até o vencimento.':'Saldo deste lote indisponível para novos envios.'));
        return card;
      }));
      if(!data.lots.length)$('#wallet-lots').append(node('p','Nenhum lote de teste recebido. Não há compra ou recarga nesta página.'));
      $('#wallet-events').replaceChildren(...data.events.map(e=>{
        const li=document.createElement('li');li.append(node('strong',`${kinds[e.kind]||'Movimentação'} · ${e.units}`),node('span',date(e.created_at)));return li;
      }));
      if(!data.events.length)$('#wallet-events').append(node('li','Nenhuma movimentação por enquanto.'));
      status.textContent='Carteira de teste atualizada.';
    }catch{status.textContent='A conexão falhou. Tente atualizar novamente.';}
    finally{busy=false;$('#wallet-refresh').disabled=false;}
  }
  $('#wallet-refresh').addEventListener('click',refresh);refresh();
})();
