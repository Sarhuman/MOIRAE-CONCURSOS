'use strict';
const $ = selector => document.querySelector(selector);
let csrf = '', session = null, pending = null, busy = false;
function message(text) { $('#status').textContent = text; }
function lock(value) { busy = value; document.querySelectorAll('button').forEach(button => { button.disabled = value; }); }
async function api(path, body) {
  const response = await fetch('/api' + path, {method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', headers: body === undefined ? {} : {'Content-Type':'application/json', 'X-CSRF-Token':csrf}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401) showAuth();
    throw new Error(typeof result.detail === 'string' ? result.detail : 'Confira os dados e tente novamente.');
  }
  return result;
}
function showAuth() { csrf=''; session=null; pending=null; $('#auth-panel').hidden=false; $('#practice-panel').hidden=true; $('#logout').hidden=true; }
function showPractice() { $('#auth-panel').hidden=true; $('#practice-panel').hidden=false; $('#logout').hidden=false; }
function quota(value) { const planLabel=document.querySelector("#study-plan"); if(planLabel)planLabel.textContent="Piloto · Plano "+(value.plan || "Free"); if(value.unlimited){$('#quota').textContent=`Plano ${value.plan}: questões sem cota durante o acesso.`;return;} $('#quota').textContent = `${value.used} de ${value.limit} questões usadas neste mês · ${value.remaining} disponíveis`; }
function render(value) {
  session=value; pending=null;
  $('#answer-feedback').hidden=true; $('#next').hidden=true; $('#complete').hidden=true;
  $('#start').hidden=Boolean(value);
  $('#official-start').hidden=Boolean(value);
  $('#question-panel').hidden=!value || !value.question;
  if (!value) return;
  if(value.status==='completed') { $('#question-panel').hidden=true; $('#complete').hidden=false; $('#summary').textContent=`Atividade concluída: ${value.answered} de ${value.total} questões respondidas. Escolha Fazer outra atividade para iniciar um novo bloco.`; return; }
  quota(value.quota);
  if (!value.question) { $('#complete').hidden=false; return; }
  const q=value.question;
  $('#question-meta').textContent=`${q.area} · ${q.subject} · ${q.source}`;
  $('#progress').textContent=`Questão ${value.answered+1} de ${value.total}`+(value.plan?` · bloco de ${value.plan.minutes} min (estimativa)`:'');
  $('#question-title').textContent=q.prompt;
  $('#choices').hidden=false;
  $('#choices').disabled=false;
  $('#answer-form button').hidden=false;
  const options=q.options.map(option=>{const label=document.createElement('label');const input=document.createElement('input');input.type='radio';input.name='choice';input.value=option.id;input.required=true;label.append(input,document.createTextNode(option.id.toUpperCase()+'. '+option.text));return label;});
  $('#options').replaceChildren(...options);
}
async function resume() { const result=await api('/practice/current');showPractice();quota(result.quota);render(result.session); }
async function action(work) { if(busy)return;lock(true);message('');try{await work();}catch(error){message(error.message || 'Não foi possível concluir. Tente novamente.');}finally{lock(false);} }
$('#auth-form').addEventListener('submit',event=>{event.preventDefault();const mode=event.submitter?.value || 'login';if(mode==='register'&&(!$('#register-terms').checked||!$('#register-adult').checked)){message('Para criar a conta de teste, aceite os termos e confirme que tem 18 anos ou mais.');return;}action(async()=>{const result=await api('/auth/'+mode,{email:$('#email').value,password:$('#password').value,...(mode==='register'?{accept_terms:$('#register-terms').checked,adult_pilot:$('#register-adult').checked}:{})});csrf=result.csrf;$('#password').value='';if(mode==='register'){message('Conta criada. Abra Minha conta para confirmar seu e-mail.');return;}await resume();message(mode==='register'?'Conta criada. Confirme seu e-mail na área Minha conta para começar.':'Você entrou. Vamos continuar?');});});
$('#logout').addEventListener('click',()=>action(async()=>{await api('/auth/logout',{});showAuth();message('Você saiu da conta.');}));
async function start() { await action(async()=>{render(await api('/practice/start',{}));}); }
$('#refresh').addEventListener('click',()=>action(resume));
$('#official-start').addEventListener('click',()=>action(async()=>{render(await api('/practice/enem-2025/start',{}));}));
$('#start').addEventListener('click',start);$('#again').addEventListener('click',start);
$('#answer-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  if(!session?.question)return;
  const choice=new FormData($('#answer-form')).get('choice');if(!choice)return;
  if(!pending || pending.choice!==choice)pending={session_id:session.id,question_id:session.question.id,choice,key:crypto.randomUUID()};
  // Guardar a chave em memória permite repetir com segurança após falha de rede.
  const answeredQuestion=session.question;
  const result=await api('/practice/answer',pending);
  session=result.session;quota(session.quota);$('#choices').disabled=true;$('#answer-form button').hidden=true;
  $('#answer-feedback').textContent=(result.correct?'Você acertou!':'Resposta correta: '+result.answer.toUpperCase()+'. '+(answeredQuestion.options.find(option=>option.id===result.answer)?.text || ''))+'\n'+result.explanation;
  if(result.review_schedule){$('#answer-feedback').textContent+='\nPróxima revisão: '+new Date(result.review_schedule.due_at*1000).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'})+'.';}
  const detail=document.createElement('details'), heading=document.createElement('summary'), list=document.createElement('ul');
  heading.textContent='Entenda cada alternativa'; detail.append(heading,list);
  for(const option of result.alternatives || []){const item=document.createElement('li');item.textContent=option.id.toUpperCase()+'. '+option.text+' — '+(option.correct?'Correta. ':'')+option.explanation;list.append(item);}
  if(result.alternatives?.length)$('#answer-feedback').append(detail);
  $('#answer-feedback').hidden=false;$('#answer-feedback').focus();
  $('#next').hidden=session.status==='completed';
  if(session.status==='completed'){$('#choices').hidden=true;$('#complete').hidden=false;$('#summary').textContent=`Você acertou ${result.summary.correct} de ${result.summary.total} questões nesta atividade. Se este foi seu diagnóstico, consulte o resultado no link acima.`;}
});});
$('#next').addEventListener('click',()=>{render(session);$('#question-title').scrollIntoView({block:'center'});});
action(async()=>{try{const result=await api('/auth/me');csrf=result.csrf;await resume();}catch(error){showAuth();if(!error.message.includes('Entre na sua conta'))throw error;}});
