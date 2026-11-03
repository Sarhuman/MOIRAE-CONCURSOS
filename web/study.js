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
function quota(value) { if(value.unlimited){$('#quota').textContent=`Plano ${value.plan}: questões sem cota durante o acesso.`;return;} $('#quota').textContent = `${value.used} de ${value.limit} questões usadas neste mês · ${value.remaining} disponíveis`; }
function render(value) {
  session=value; pending=null;
  $('#answer-feedback').hidden=true; $('#next').hidden=true; $('#complete').hidden=true;
  $('#start').hidden=Boolean(value);
  $('#question-panel').hidden=!value || !value.question;
  if (!value) return;
  quota(value.quota);
  if (!value.question) { $('#complete').hidden=false; return; }
  const q=value.question;
  $('#question-meta').textContent=`${q.area} · ${q.subject}`;
  $('#progress').textContent=`Questão ${value.answered+1} de ${value.total}`;
  $('#question-title').textContent=q.prompt;
  $('#choices').disabled=false;
  $('#answer-form button').hidden=false;
  const options=q.options.map(option=>{const label=document.createElement('label');const input=document.createElement('input');input.type='radio';input.name='choice';input.value=option.id;input.required=true;label.append(input,document.createTextNode(option.text));return label;});
  $('#options').replaceChildren(...options);
}
async function resume() { const result=await api('/practice/current');showPractice();quota(result.quota);render(result.session); }
async function action(work) { if(busy)return;lock(true);message('');try{await work();}catch(error){message(error.message || 'Não foi possível concluir. Tente novamente.');}finally{lock(false);} }
$('#auth-form').addEventListener('submit',event=>{event.preventDefault();const mode=event.submitter?.value || 'login';if(mode==='register'&&(!$('#register-terms').checked||!$('#register-adult').checked)){message('Para criar a conta de teste, aceite os termos e confirme que tem 18 anos ou mais.');return;}action(async()=>{const result=await api('/auth/'+mode,{email:$('#email').value,password:$('#password').value,...(mode==='register'?{accept_terms:$('#register-terms').checked,adult_pilot:$('#register-adult').checked}:{})});csrf=result.csrf;$('#password').value='';if(mode==='register'){message('Conta criada. Abra Minha conta para confirmar seu e-mail.');return;}await resume();message(mode==='register'?'Conta criada. Confirme seu e-mail na área Minha conta para começar.':'Você entrou. Vamos continuar?');});});
$('#logout').addEventListener('click',()=>action(async()=>{await api('/auth/logout',{});showAuth();message('Você saiu da conta.');}));
async function start() { await action(async()=>{render(await api('/practice/start',{}));}); }
$('#refresh').addEventListener('click',()=>action(resume));
$('#start').addEventListener('click',start);$('#again').addEventListener('click',start);
$('#answer-form').addEventListener('submit',event=>{event.preventDefault();action(async()=>{
  if(!session?.question)return;
  const choice=new FormData($('#answer-form')).get('choice');if(!choice)return;
  if(!pending || pending.choice!==choice)pending={session_id:session.id,question_id:session.question.id,choice,key:crypto.randomUUID()};
  // Guardar a chave em memória permite repetir com segurança após falha de rede.
  const result=await api('/practice/answer',pending);
  session=result.session;quota(session.quota);$('#choices').disabled=true;$('#answer-form button').hidden=true;
  $('#answer-feedback').textContent=(result.correct?'Você acertou!':'A resposta correta é a alternativa '+result.answer.toUpperCase()+'.')+'\n'+result.explanation;
  $('#answer-feedback').hidden=false;$('#answer-feedback').focus();
  $('#next').hidden=session.status==='completed';
  if(session.status==='completed'){$('#complete').hidden=false;$('#summary').textContent=`Você acertou ${result.summary.correct} de ${result.summary.total} questões nesta atividade.`;}
});});
$('#next').addEventListener('click',()=>{render(session);$('#question-title').scrollIntoView({block:'center'});});
action(async()=>{try{const result=await api('/auth/me');csrf=result.csrf;await resume();}catch(error){showAuth();if(!error.message.includes('Entre na sua conta'))throw error;}});
