'use strict';
(()=>{
  const $=s=>document.querySelector(s),status=$('#essay-status'),drafts=new Map(),view=globalThis.EssayView;
  let csrf='',current=null,sendKey=null,busy=false,ready=false,sendDirty=false,selected='';
  const showError=e=>{status.textContent=e.message;};
  const date=value=>new Date(value*1000).toLocaleString('pt-BR');
  async function api(path,body){
    let r;try{r=await fetch(path,{credentials:'same-origin',headers:body?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},...(body?{method:'POST',body:JSON.stringify(body)}:{})});}catch{throw new Error('A conexão falhou. Seu rascunho continua nesta aba. Tente novamente.');}
    const d=await r.json();if(!r.ok)throw new Error(d.detail||'Não foi possível concluir. Seu rascunho continua nesta aba.');return d;
  }
  function element(tag,text,className){const e=document.createElement(tag);e.textContent=text;if(className)e.className=className;return e;}
  function draftKey(){return current?`${current.id}:${selected}`:'';}
  function remember(){if(current&&selected){const key=draftKey(),old=drafts.get(key);drafts.set(key,{text:$('#essay-rewrite').value,key:old?.key||null});}}
  function choose(id){remember();selected=id;$('#essay-annotation').value=id;const a=current?.result?.annotations.find(a=>a.id===id);$('#essay-guidance').textContent=a?`C${a.competency} · ${a.guidance}`:'';$('#essay-rewrite').value=drafts.get(draftKey())?.text||'';document.querySelectorAll('[data-annotation]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.annotation===id)));}
  async function history(){
    const d=await api('/api/essays');$('#essay-wallet-option').disabled=!d.wallet_enabled;$('#essay-balance').textContent=`Franquia demonstrativa: ${d.remaining}. Carteira sandbox: ${d.wallet_remaining||0}. ${d.notice}`;
    $('#essay-history').replaceChildren(...d.items.map(item=>{const li=document.createElement('li'),b=element('button',`${item.theme} · ${view.states[item.status]||'Estado indisponível'} · ${date(item.created_at)}`);b.type='button';b.onclick=()=>action(async()=>{remember();await load(item.id);$('#essay-title').focus();});li.append(b);return li;}));
    if(!d.items.length)$('#essay-history').append(element('li','Seu primeiro envio vai aparecer aqui.'));
  }
  function compare(){const rewrite=current.rewrites.find(r=>r.id===$('#essay-version').value);const a=current.result?.annotations.find(a=>a.id===rewrite?.annotation_id);$('#compare-original').textContent=a?.quote||'';$('#compare-rewrite').textContent=rewrite?.text||'';}
  async function load(id){
    const data=await api('/api/essays/'+id);current=data;selected='';$('#essay-detail').hidden=false;$('#essay-title').textContent=current.theme;$('#essay-title').tabIndex=-1;$('#essay-state').textContent=(view.states[current.status]||'Estado indisponível')+' · '+(current.funding==='sandbox_wallet'?'Carteira sandbox':'Franquia demonstrativa');
    $('#essay-process').hidden=current.status!=='received';$('#essay-result').replaceChildren();$('#essay-original').textContent=current.text;$('#rewrite-form').hidden=!current.result;$('#essay-rewrite').value='';
    if(current.result){
      const result=current.result;$('#essay-result').append(element('p',result.notice));const grid=element('div','','essay-scores');
      result.competencies.forEach(c=>{const card=document.createElement('article');card.append(element('strong',`C${c.id}: ${c.score}/200`),element('p',c.explanation));grid.append(card);});$('#essay-result').append(grid);
      $('#essay-original').replaceChildren(...view.segments(current.text,result.annotations).map(part=>{if(!part.annotations.length)return document.createTextNode(part.text);const a=part.annotations[0],b=element('button',part.text,`essay-mark tone-${a.competency}`);b.type='button';b.dataset.annotation=a.id;b.setAttribute('aria-label',`${part.annotations.map(a=>'C'+a.competency).join(', ')}: ${part.text}`);b.setAttribute('aria-pressed','false');b.onclick=()=>{if(!busy){choose(a.id);$('#essay-annotation').focus();}};return b;}));
      $('#essay-annotation').replaceChildren(...result.annotations.map(a=>{const o=element('option',`C${a.competency} · ${a.quote}`);o.value=a.id;return o;}));if(result.annotations.length)choose(result.annotations[0].id);else $('#rewrite-form').hidden=true;
    }
    $('#essay-rewrites').replaceChildren(...current.rewrites.map((r,i)=>{const li=document.createElement('li');li.append(element('p',`Versão ${i+1} · ${date(r.created_at)}`),element('p',r.text,'essay-rewrite-version'));return li;}));
    $('#essay-comparison').hidden=!current.rewrites.length;
    $('#essay-version').replaceChildren(...current.rewrites.map((r,i)=>{const o=element('option',`Versão ${i+1} · ${date(r.created_at)}`);o.value=r.id;return o;}));if(current.rewrites.length){$('#essay-version').value=current.rewrites.at(-1).id;compare();}
  }
  async function action(fn){if(busy||!ready)return;busy=true;document.querySelectorAll('form input,form textarea,form select,button,#essay-version').forEach(b=>b.disabled=true);try{await fn();}catch(e){showError(e);}finally{busy=false;document.querySelectorAll('form input,form textarea,form select,button,#essay-version').forEach(b=>b.disabled=false);}}
  $('#essay-form').addEventListener('input',()=>{sendKey=null;sendDirty=true;});
  $('#essay-rewrite').addEventListener('input',()=>{remember();drafts.get(draftKey()).key=null;});
  $('#essay-annotation').onchange=()=>choose($('#essay-annotation').value);$('#essay-version').onchange=compare;
  window.addEventListener('beforeunload',e=>{if(sendDirty||[...drafts.values()].some(d=>d.text)){e.preventDefault();e.returnValue='';}});
  $('#essay-form').onsubmit=e=>{e.preventDefault();action(async()=>{remember();sendKey=sendKey||crypto.randomUUID();const d=await api('/api/essays',{key:sendKey,theme:$('#essay-theme').value,text:$('#essay-text').value,funding:$('#essay-funding').value});sendDirty=false;await load(d.id);await history();status.textContent='Texto salvo. O crédito de teste está reservado; gere a demonstração abaixo.';$('#essay-title').focus();});};
  $('#essay-process').onclick=()=>action(async()=>{const id=current.id;status.textContent='Preparando a demonstração…';await api(`/api/essays/${id}/process`,{});await load(id);await history();status.textContent=current.status==='completed'?'Demonstração pronta. As notas são fixas, sem avaliação por IA.':'A demonstração falhou; a reserva foi liberada.';});
  $('#rewrite-form').onsubmit=e=>{e.preventDefault();action(async()=>{remember();const key=draftKey(),draft=drafts.get(key);draft.key=draft.key||crypto.randomUUID();const id=current.id;await api(`/api/essays/${id}/rewrites`,{key:draft.key,annotation_id:selected,text:draft.text});drafts.delete(key);await load(id);status.textContent='Reescrita guardada. Compare as versões abaixo; não houve avaliação nem consumo adicional.';});};
  (async()=>{const me=await api('/api/auth/me');csrf=me.csrf;await history();ready=true;$('#essay-send').disabled=false;status.textContent='Oficina de demonstração. Os textos enviados ficam na sua conta.';})().catch(showError);
})();
