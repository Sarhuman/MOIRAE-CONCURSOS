'use strict';
const $ = selector => document.querySelector(selector);
let paid=false;
let csrf='',exam=null,index=0,lastSaved='',queue=Promise.resolve(),selectedDay=1,startKey=null;
let baseTime=performance.now(),serverTime=0,expiryRequested=false,warningShown=false;
function say(text){$('#exam-status').textContent=text;}
function quota(q){paid=q.unlimited;if(paid){$('#exam-quota').textContent=`Plano ${q.plan}: este treino não consome a cota Free.`;return;}$('#exam-quota').textContent=`Você usou ${q.used} de ${q.limit} questões neste mês. Saldo: ${q.remaining}. Renova em ${new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',dateStyle:'short'}).format(new Date(q.resets_at))}.`;}
async function api(path,body){
  const r=await fetch('/api'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const value=await r.json();
  if(!r.ok){if(r.status===401){$('#exam-login').hidden=false;$('#exam-setup').hidden=true;$('#exam-work').hidden=true;}throw new Error(typeof value.detail==='string'?value.detail:'Confira os campos e tente novamente.');}
  return value;
}
function perform(work){
  queue=queue.then(async()=>{document.querySelectorAll('button').forEach(b=>b.disabled=true);try{await work();}catch(e){say(e.message || 'Não foi possível salvar. Mantenha esta página aberta e tente novamente.');}finally{document.querySelectorAll('button').forEach(b=>b.disabled=false);}});
  return queue;
}
function card(){
  $('#answer-card').replaceChildren(...exam.items.map((item,i)=>{const b=document.createElement('button');b.type='button';b.textContent=`${i+1}${item.choice?' ●':''}${item.flagged?' ★':''}`;b.setAttribute('aria-label',`Questão ${i+1}${item.choice?', respondida':', em branco'}${item.flagged?', marcada para revisar':''}`);b.setAttribute('aria-current',String(i===index));if(item.choice)b.classList.add('answered');b.addEventListener('click',()=>perform(async()=>{index=i;renderQuestion();$('#exam-question').scrollIntoView({block:'start'});}));return b;}));
}
function renderQuestion(){
  if(!exam?.items[index])return;
  const item=exam.items[index],q=item.question;
  $('#exam-question-title').textContent=`Questão ${index+1} · ${q.area}`;$('#exam-prompt').textContent=q.prompt;
  const options=[...q.options,{id:'',text:'Deixar em branco'}].map(option=>{const label=document.createElement('label'),input=document.createElement('input');input.type='radio';input.name='choice';input.value=option.id;input.checked=(item.choice||'')===option.id;label.append(input,document.createTextNode(option.text));return label;});
  $('#exam-options').replaceChildren(...options);$('#exam-flag').checked=item.flagged;$('#item-save-status').textContent='As alterações são salvas quando você escolhe uma alternativa ou marca para revisar.';card();
}
function result(){
  $('#exam-work').hidden=true;$('#exam-setup').hidden=true;$('#exam-result').hidden=false;
  $('#exam-summary').textContent=`${exam.status==='expired'?'O tempo terminou.':'Você entregou o simulado.'} Acertos: ${exam.result.correct} de ${exam.result.total}. Questões em branco: ${exam.result.blank}. Sem estimativa de TRI.`;
  $('#essay-result-status').textContent=exam.day===1?'A redação salva foi preservada. O plano Free não inclui correção nem nota.':'';
  $('#saved-essay-panel').hidden=exam.day!==1;$('#saved-essay').textContent=exam.essay || 'Nenhum texto foi salvo.';
  $('#exam-review').replaceChildren(...exam.items.map((item,i)=>{const article=document.createElement('article'),h=document.createElement('h3'),p=document.createElement('p'),explanation=document.createElement('p');h.textContent=`Questão ${i+1}`;p.textContent=`${item.choice?'Sua resposta: '+item.choice.toUpperCase():'Em branco'} · Correta: ${item.answer.toUpperCase()}`;explanation.textContent=item.explanation;article.append(h,p,explanation);return article;}));
  const unsaved=$('#essay-text').value;
  if(exam.day===1 && unsaved && unsaved!==exam.essay){$('#unsaved-panel').hidden=false;$('#unsaved-text').value=unsaved;say('Há um trecho digitado que não chegou ao servidor antes do encerramento. Você pode copiá-lo abaixo; ele não faz parte da redação entregue.');}
}
function apply(value){
  const changed=exam?.id!==value.id;exam=value;serverTime=value.server_now;baseTime=performance.now();quota(value.quota);
  if(changed){index=0;lastSaved=value.essay;$('#essay-text').value=value.essay;warningShown=false;expiryRequested=false;$('#time-warning').textContent='';$('#unsaved-panel').hidden=true;}
  if(value.status!=='active'){result();return;}
  $('#exam-work').hidden=false;$('#exam-setup').hidden=true;$('#exam-result').hidden=true;
  $('#exam-name').textContent=`Treino do ${value.day}º dia · ${value.items.length} questões`;
  $('#essay-panel').hidden=value.day!==1;$('#open-essay').hidden=value.day!==1;
  if(value.essay_prompt){$('#essay-title').textContent=value.essay_prompt.title;$('#essay-instructions').textContent=value.essay_prompt.instructions;$('#essay-notice').textContent=value.essay_prompt.notice;$('#supporting-texts').replaceChildren(...value.essay_prompt.supporting_texts.map(text=>{const p=document.createElement('p');p.textContent=text;return p;}));}
  card();if(changed)renderQuestion();tick();
}
async function refresh(){const value=await api('/exams/current');quota(value.quota);if(value.exam)apply(value.exam);else{$('#exam-setup').hidden=false;}}
function tick(){
  if(!exam || exam.status!=='active')return;
  const left=Math.max(0,exam.deadline-serverTime-Math.floor((performance.now()-baseTime)/1000));
  $('#timer').textContent=`${String(Math.floor(left/60)).padStart(2,'0')}:${String(left%60).padStart(2,'0')}`;
  if(left<=300 && !warningShown){$('#time-warning').textContent='Faltam cinco minutos ou menos. Confira suas respostas e se o rascunho foi salvo.';warningShown=true;}
  if(left===0 && !expiryRequested){expiryRequested=true;perform(refresh);}
}
async function saveItem(){
  if(!exam || exam.status!=='active')return;
  const item=exam.items[index],choice=new FormData($('#exam-answer-form')).get('choice')||null;
  const next=await api(`/exams/${exam.id}/item`,{question_id:item.question.id,choice,flagged:$('#exam-flag').checked,revision:item.revision});
  apply(next);$('#item-save-status').textContent=next.status==='active'?'Resposta e marcação salvas.':'O prazo terminou; a alteração não foi aceita.';
}
async function saveEssay(){
  if(!exam || exam.day!==1 || exam.status!=='active' || $('#essay-text').value===lastSaved)return;
  const text=$('#essay-text').value;$('#essay-autosave').textContent='Salvando rascunho…';
  try{const next=await api(`/exams/${exam.id}/essay`,{text,revision:exam.essay_revision});apply(next);if(next.status==='active'){lastSaved=text;$('#essay-autosave').textContent=$('#essay-text').value===text?'Rascunho salvo no servidor.':'Há alterações novas; aguarde o próximo salvamento.';}}
  catch(error){$('#essay-autosave').textContent='Não foi possível salvar. Copie seu texto e tente novamente antes de sair.';throw error;}
}
let saveTimer;
$('#essay-text').addEventListener('input',()=>{$('#essay-autosave').textContent='Há alterações ainda não salvas.';clearTimeout(saveTimer);saveTimer=setTimeout(()=>perform(saveEssay),1200);});
$('#essay-save').addEventListener('click',()=>perform(saveEssay));
$('#exam-answer-form').addEventListener('submit',event=>{event.preventDefault();perform(saveItem);});
$('#exam-answer-form').addEventListener('change',()=>perform(saveItem));
$('#open-essay').addEventListener('click',()=>$('#essay-panel').scrollIntoView({block:'start'}));
$('#exam-refresh').addEventListener('click',()=>perform(async()=>{await saveEssay();await refresh();if(exam?.status==='active')renderQuestion();}));
document.querySelectorAll('[data-day]').forEach(button=>button.addEventListener('click',()=>{selectedDay=Number(button.dataset.day);startKey=crypto.randomUUID();$('#start-description').textContent=selectedDay===1?'Primeiro dia: 6 questões e redação digitada em 30 minutos.':'Segundo dia: 6 questões em 15 minutos.';$('#start-cost').textContent=paid?'Seu plano ativo não tem cota de questões.':'Este treino usa 6 questões da sua cota, inclusive se não terminar.';$('#start-confirm').showModal();}));
$('#cancel-start').addEventListener('click',()=>$('#start-confirm').close());
$('#confirm-start').addEventListener('click',()=>perform(async()=>{const value=await api('/exams/start',{day:selectedDay,key:startKey});$('#start-confirm').close();say('Simulado iniciado. O cronômetro continua mesmo se você sair.');apply(value);}));
$('#finish-exam').addEventListener('click',()=>{const blanks=exam.items.filter(i=>!i.choice).length;$('#finish-description').textContent=`Você tem ${blanks} questão(ões) em branco. O rascunho da redação será salvo antes da entrega, se ainda houver tempo.`;$('#finish-confirm').showModal();});
$('#cancel-finish').addEventListener('click',()=>$('#finish-confirm').close());
$('#confirm-finish').addEventListener('click',()=>perform(async()=>{await saveEssay();if(exam.status==='active')apply(await api(`/exams/${exam.id}/finish`,{}));$('#finish-confirm').close();}));
$('#new-exam').addEventListener('click',()=>{$('#exam-result').hidden=true;$('#exam-setup').hidden=false;});
window.addEventListener('beforeunload',event=>{if(exam?.status==='active' && $('#essay-text').value!==lastSaved){event.preventDefault();event.returnValue='';}});
document.addEventListener('visibilitychange',()=>{if(!document.hidden && exam?.status==='active')perform(async()=>{await saveEssay();await refresh();});});
setInterval(tick,1000);
setInterval(()=>{if(exam?.status==='active' && !document.hidden)perform(async()=>{await saveEssay();await refresh();});},15000);
perform(async()=>{try{const me=await api('/auth/me');csrf=me.csrf;await refresh();}catch(error){$('#exam-login').hidden=false;say(error.message);}});
