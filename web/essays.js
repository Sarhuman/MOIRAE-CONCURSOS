'use strict';
(()=>{
  const $=s=>document.querySelector(s), status=$('#essay-status');
  let csrf='',current=null,sendKey=null,rewriteKey=null,busy=false;
  const showError=e=>{status.textContent=e.message;};
  async function api(path,body){
    const r=await fetch(path,{credentials:'same-origin',headers:body?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},...(body?{method:'POST',body:JSON.stringify(body)}:{})});
    const d=await r.json();if(!r.ok)throw new Error(d.detail||'Não foi possível concluir. Seu texto continua no campo para tentar novamente.');return d;
  }
  function element(tag,text,className){const e=document.createElement(tag);e.textContent=text;if(className)e.className=className;return e;}
  async function history(){
    const d=await api('/api/essays');$('#essay-balance').textContent=`${d.remaining} créditos de teste disponíveis. ${d.notice}`;
    $('#essay-history').replaceChildren(...d.items.map(item=>{const li=document.createElement('li'),b=element('button',`${item.theme} · ${item.status} · ${new Date(item.created_at*1000).toLocaleString('pt-BR')}`);b.type='button';b.onclick=()=>{if(!busy)load(item.id).catch(showError);};li.append(b);return li;}));
    if(!d.items.length)$('#essay-history').append(element('li','Seu primeiro envio vai aparecer aqui.'));
  }
  function guidance(){const a=current?.result?.annotations.find(a=>a.id===$('#essay-annotation').value);$('#essay-guidance').textContent=a?.guidance||'';}
  async function load(id){
    current=await api('/api/essays/'+id);$('#essay-detail').hidden=false;$('#essay-title').textContent=current.theme;$('#essay-state').textContent=`Estado: ${current.status}. ${current.error?'A demonstração falhou. A reserva foi liberada; você pode fazer um novo envio.':''}`;
    $('#essay-process').hidden=current.status!=='received';$('#essay-result').replaceChildren();$('#essay-original').textContent=current.text;
    $('#rewrite-form').hidden=!current.result;$('#essay-rewrite').value='';rewriteKey=null;
    if(current.result){
      const result=current.result;$('#essay-result').append(element('p',result.notice));const grid=element('div','','essay-scores');
      result.competencies.forEach(c=>{const card=document.createElement('article');card.append(element('strong',`C${c.id}: ${c.score}/200`),element('p',c.explanation));grid.append(card);});$('#essay-result').append(grid);
      const annotations=[...result.annotations].sort((a,b)=>a.start-b.start);let offset=0;const nodes=[];
      for(const a of annotations){if(a.start<offset)continue;nodes.push(document.createTextNode(current.text.slice(offset,a.start)));nodes.push(element('mark',current.text.slice(a.start,a.end)));offset=a.end;}
      nodes.push(document.createTextNode(current.text.slice(offset)));$('#essay-original').replaceChildren(...nodes);
      $('#essay-annotation').replaceChildren(...result.annotations.map(a=>{const o=element('option',`C${a.competency} · ${a.quote}`);o.value=a.id;return o;}));guidance();
    }
    $('#essay-rewrites').replaceChildren(...current.rewrites.map(r=>{const li=document.createElement('li');li.append(element('p',new Date(r.created_at*1000).toLocaleString('pt-BR')),element('p',r.text,'essay-rewrite-version'));return li;}));
  }
  async function action(fn){if(busy)return;busy=true;document.querySelectorAll('form button,#essay-process').forEach(b=>b.disabled=true);try{await fn();}catch(e){showError(e);}finally{busy=false;document.querySelectorAll('form button,#essay-process').forEach(b=>b.disabled=false);}}
  $('#essay-form').addEventListener('input',()=>{sendKey=null;});
  $('#rewrite-form').addEventListener('input',()=>{rewriteKey=null;});$('#essay-annotation').onchange=()=>{rewriteKey=null;guidance();};
  $('#essay-form').onsubmit=e=>{e.preventDefault();action(async()=>{sendKey=sendKey||crypto.randomUUID();const d=await api('/api/essays',{key:sendKey,theme:$('#essay-theme').value,text:$('#essay-text').value});await load(d.id);await history();status.textContent='Texto salvo. O crédito de teste está reservado; gere a demonstração ao lado.';});};
  $('#essay-process').onclick=()=>action(async()=>{const id=current.id;status.textContent='Gerando demonstração…';await api(`/api/essays/${id}/process`,{});await load(id);await history();status.textContent=current.status==='completed'?'Demonstração pronta. As notas são fixas, sem avaliação por IA.':'A demonstração falhou; a reserva foi liberada.';});
  $('#rewrite-form').onsubmit=e=>{e.preventDefault();action(async()=>{rewriteKey=rewriteKey||crypto.randomUUID();const id=current.id;await api(`/api/essays/${id}/rewrites`,{key:rewriteKey,annotation_id:$('#essay-annotation').value,text:$('#essay-rewrite').value});await load(id);status.textContent='Reescrita guardada. Não houve consumo de crédito adicional nem avaliação.';});};
  (async()=>{const me=await api('/api/auth/me');csrf=me.csrf;await history();$('#essay-send').disabled=false;status.textContent='Oficina de demonstração. Os textos enviados ficam na sua conta.';})().catch(showError);
})();
