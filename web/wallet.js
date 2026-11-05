'use strict';
(() => {
  const $ = s => document.querySelector(s);
  const status = $('#wallet-status');
  const kinds = {grant:'Créditos de teste recebidos',reserve:'Crédito reservado',consume:'Crédito consumido',release:'Reserva liberada',refund:'Crédito estornado',revoke:'Lote revogado'};
  const states = {active:'Ativo',expired:'Vencido',revoked:'Revogado'};
  const date = n => new Date(n*1000).toLocaleString('pt-BR');
  const node = (tag,text) => { const e=document.createElement(tag);e.textContent=text;return e; };
  let busy=false;
  let pack=null,packKey='',csrf='';
  const money=n=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n/100);
  async function packs() {
    try {
      const r=await fetch('/api/sandbox/credit-packs',{cache:'no-store'});if(!r.ok)throw new Error();
      const data=await r.json();$('#pack-notice').textContent=data.notice;
      $('#wallet-packs').replaceChildren(...data.packs.map(p=>{
        const card=node('article','');card.className='wallet-lot';const button=node('button',data.checkout_enabled?'Testar pedido':'Compra de teste indisponível');
        button.type='button';button.className='button';button.disabled=!data.checkout_enabled;
        button.addEventListener('click',()=>{pack=p;packKey=crypto.randomUUID();$('#pack-description').textContent=`${p.credits} créditos sandbox · ${money(p.price_cents)} · validade configurada: ${data.validity_days} dias a partir da concessão. Pagamento único, sem parcelamento. A oficina exige plano de teste ativo.`;$('#pack-confirm').showModal();});
        card.append(node('h3',`${p.credits} créditos sandbox`),node('p',money(p.price_cents)+' · acréscimo de 10% já incluído'),button);return card;
      }));
    }catch{$('#pack-notice').textContent='Não foi possível consultar os pacotes de teste. Atualize a página.';}
  }
  $('#pack-cancel').addEventListener('click',()=>$('#pack-confirm').close());
  $('#pack-go').addEventListener('click',async()=>{
    if(busy||!pack)return;busy=true;$('#pack-go').disabled=true;
    try{
      const me=await fetch('/api/auth/me',{cache:'no-store'});if(!me.ok)throw new Error('Entre na conta antes de continuar.');csrf=(await me.json()).csrf;
      const r=await fetch('/api/sandbox/credit-packs/checkout',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({product:pack.id,key:packKey})});const data=await r.json();
      if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Não foi possível criar o pedido.');
      if(data.mode!=='sandbox')throw new Error('Ambiente de pagamento inesperado.');location.assign(data.checkout_url);
    }catch(e){$('#pack-description').textContent=e.message;}
    finally{busy=false;$('#pack-go').disabled=false;}
  });
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
      if(!data.lots.length)$('#wallet-lots').append(node('p','Nenhum lote de teste recebido. Consulte a disponibilidade dos pacotes abaixo.'));
      $('#wallet-events').replaceChildren(...data.events.map(e=>{
        const li=document.createElement('li');li.append(node('strong',`${kinds[e.kind]||'Movimentação'} · ${e.units}`),node('span',date(e.created_at)));return li;
      }));
      if(!data.events.length)$('#wallet-events').append(node('li','Nenhuma movimentação por enquanto.'));
      status.textContent='Carteira de teste atualizada.';
    }catch{status.textContent='A conexão falhou. Tente atualizar novamente.';}
    finally{busy=false;$('#wallet-refresh').disabled=false;}
  }
  $('#wallet-refresh').addEventListener('click',refresh);refresh();packs();
})();
