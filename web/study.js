'use strict';
const $ = selector => document.querySelector(selector);
let csrf = '', session = null, pending = null, busy = false, authMode = 'login';
function message(text) { $('#status').textContent = text; }
function lock(value) { busy = value; document.querySelectorAll('button').forEach(button => { button.disabled = value; }); $('#auth-submit').textContent=value?(authMode==='register'?'Criando sua conta…':'Entrando…'):(authMode==='register'?'Criar minha conta Free':'Entrar na minha conta'); }
async function api(path, body) {
  const response = await fetch('/api' + path, {method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', headers: body === undefined ? {} : {'Content-Type':'application/json', 'X-CSRF-Token':csrf}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401) showAuth();
    throw new Error(typeof result.detail === 'string' ? result.detail : 'Confira os dados e tente novamente.');
  }
  return result;
}
function showAuth() { $('#password').value='';$('#register-terms').checked=false;$('#register-adult').checked=false;csrf=''; session=null; pending=null; $('#auth-panel').hidden=false; $('#onboarding-panel').hidden=true; $('#practice-panel').hidden=true; $('#logout').hidden=true; $('#study-plan').textContent='Área do aluno'; }
function showPractice() { $('#auth-panel').hidden=true; $('#onboarding-panel').hidden=true; $('#practice-panel').hidden=false; $('#logout').hidden=false; }
const planNames={free:'Free',essencial:'Essencial',avancado:'Avançado'};
function quota(value) {
  const name=planNames[value.plan]||'Free';$('#study-plan').textContent='Piloto · '+name;
  const paid=Boolean(value.unlimited);$('#member-access').classList.toggle('is-paid',paid);
  $('#member-eyebrow').textContent=paid?'ACESSO PAGO DE TESTE':'SUA CONTA GRATUITA';
  $('#member-title').textContent=paid?`Seu acesso ${name}.`:'Seu Free está pronto para estudar.';
  $('#member-description').textContent=paid?'Pratique sem cota de questões durante o acesso e acompanhe suas respostas.':`${value.remaining} de ${value.limit} questões disponíveis neste mês. Você pode continuar sem contratar um plano.`;
  const benefits=paid?['Questões sem cota durante o acesso ativo.','Painel, erros/favoritos e sessões planejadas.','Biblioteca e acervo na sua conta.']:[`Prática e simulados compartilham as ${value.limit} questões mensais.`,'Diagnóstico inicial, explicações e último resultado.','Biblioteca introdutória e acervo após login.'];
  $('#member-benefits').replaceChildren(...benefits.map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
  $('#member-next').href=paid?'/painel':'/planos';$('#member-next').textContent=paid?'Abrir meu painel ↗':'Conhecer os acessos pagos de teste ↗';
  $('#quota-help').textContent=paid?'Seu progresso fica salvo no servidor. Painel, caderno e planejamento acompanham seu acesso pago ativo.':'O Free permite 30 questões por mês, compartilhadas com os simulados. O saldo renova no primeiro dia do mês, no horário de Brasília. Seu progresso fica salvo no servidor.';
  $('#quota').textContent=paid?`${name}: questões sem cota durante o acesso.`:`${value.used} de ${value.limit} questões usadas neste mês · ${value.remaining} disponíveis`;
}
function setAuthMode(mode,focus=false){
  if(busy)return;authMode=mode;
  const register=mode==='register';$('#auth-login-mode').setAttribute('aria-pressed',String(!register));$('#auth-register-mode').setAttribute('aria-pressed',String(register));
  $('#auth-title').textContent=register?'Sua conta Free começa aqui.':'Bom ter você de volta.';
  $('#auth-description').textContent=register?'Cadastro gratuito, sem assinatura. Confirme seu e-mail depois para liberar o conteúdo.':'Entre com seu e-mail e senha para continuar de onde parou.';
  $('#password').autocomplete=register?'new-password':'current-password';$('#password-help').textContent=register?'Crie uma senha exclusiva de 12 a 128 caracteres.':'Use sua senha de 12 a 128 caracteres.';
  $('#registration-consents').hidden=!register;for(const id of ['#register-terms','#register-adult']){$(id).disabled=!register;$(id).required=register;}
  $('#login-help').hidden=register;$('#auth-submit').textContent=register?'Criar minha conta Free':'Entrar na minha conta';message('');if(focus)$('#email').focus();
}
function showPending(me,moveFocus=false){
  $('#auth-panel').hidden=true;$('#practice-panel').hidden=true;$('#onboarding-panel').hidden=false;$('#logout').hidden=false;$('#study-plan').textContent='Conta · confirmação pendente';
  $('#onboarding-title').textContent=me.policy_accepted?'Confirme seu e-mail para começar.':'Revise os termos para continuar.';
  $('#onboarding-description').textContent=me.policy_accepted?'Seu cadastro foi salvo. Em Minha conta você pode solicitar um novo link. No piloto local, o responsável pelo servidor acessa a caixa de saída privada para abrir a confirmação. Não é necessário contratar um plano.':'Seu cadastro está preservado. Confira as políticas e a confirmação do e-mail em Minha conta; as questões ficam bloqueadas até concluir essa etapa.';
  if(moveFocus)$('#onboarding-title').focus();
}
async function openAccount(moveFocus=false){
  const me=await api('/auth/me');csrf=me.csrf;
  if(!me.email_verified||!me.policy_accepted){showPending(me,moveFocus);return false;}
  await resume(moveFocus);return true;
}
function officialStarts(hidden) {
  for(const id of ['#official-start','#official-second','#official-third','#official-fourth','#official-fifth'])$(id).hidden=hidden;
}
function render(value,moveFocus=false) {
  session=value; pending=null;
  $('#answer-feedback').hidden=true; $('#next').hidden=true; $('#complete').hidden=true;
  $('#start').hidden=Boolean(value);
  officialStarts(value?.status==='active');
  $('#question-panel').hidden=!value || !value.question;
  if (!value) return;
  if(value.status==='completed') { $('#question-panel').hidden=true; $('#complete').hidden=false; $('#summary').textContent=value.summary?`Você acertou ${value.summary.correct} de ${value.summary.total} questões nesta atividade. Escolha outra atividade para continuar.`:`Atividade concluída: ${value.answered} de ${value.total} questões respondidas. Escolha Fazer outra atividade para iniciar um novo bloco.`; if(moveFocus)$('#complete').focus(); return; }
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
  if(moveFocus)$('#question-title').focus();
}
async function resume(moveFocus=false) { const result=await api('/practice/current');showPractice();quota(result.quota);const value=result.session || result.completed;render(value,moveFocus);if(moveFocus&&!value)$('#member-title').focus(); }
async function action(work) { if(busy)return;lock(true);message('');try{await work();}catch(error){message(error.message || 'Não foi possível concluir. Tente novamente.');$('#status').focus();}finally{lock(false);} }
$('#auth-login-mode').addEventListener('click',()=>setAuthMode('login',true));
$('#auth-register-mode').addEventListener('click',()=>setAuthMode('register',true));
$('#check-access').addEventListener('click',()=>action(()=>openAccount(true)));
$('#auth-form').addEventListener('submit',event=>{
  event.preventDefault();const mode=authMode;
  if(mode==='register'&&(!$('#register-terms').checked||!$('#register-adult').checked)){message('Para criar a conta Free do piloto, aceite os termos e confirme que tem 18 anos ou mais.');$('#status').focus();return;}
  action(async()=>{
    const result=await api('/auth/'+mode,{email:$('#email').value,password:$('#password').value,...(mode==='register'?{accept_terms:$('#register-terms').checked,adult_pilot:$('#register-adult').checked}:{})});
    csrf=result.csrf;$('#password').value='';
    const ready=await openAccount(true);message(mode==='register'?'Conta Free criada. Confirme seu e-mail para começar.':ready?'Você entrou. Seu próximo passo está abaixo.':'Você entrou. Conclua a confirmação da conta para acessar as questões.');
  });
});
$('#logout').addEventListener('click',()=>action(async()=>{await api('/auth/logout',{});showAuth();message('Você saiu da conta.');$('#email').focus();}));
async function start() { await action(async()=>{render(await api('/practice/start',{}),true);}); }
$('#refresh').addEventListener('click',()=>action(()=>resume(true)));
$('#official-fifth').addEventListener('click',()=>action(async()=>{render(await api('/practice/enem-2025/batch-5/start',{}),true);}));
$('#official-fourth').addEventListener('click',()=>action(async()=>{render(await api('/practice/enem-2025/batch-4/start',{}),true);}));
$('#official-third').addEventListener('click',()=>action(async()=>{render(await api('/practice/enem-2025/batch-3/start',{}),true);}));
$('#official-second').addEventListener('click',()=>action(async()=>{render(await api('/practice/enem-2025/batch-2/start',{}),true);}));
$('#official-start').addEventListener('click',()=>action(async()=>{render(await api('/practice/enem-2025/start',{}),true);}));
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
  if(session.status==='completed'){officialStarts(false);$('#choices').hidden=true;$('#complete').hidden=false;$('#summary').textContent=`Você acertou ${result.summary.correct} de ${result.summary.total} questões nesta atividade. Se este foi seu diagnóstico, consulte o resultado no link acima.`;}
});});
$('#next').addEventListener('click',()=>{render(session,true);});
setAuthMode(new URLSearchParams(location.search).get('cadastro')==='1'?'register':'login');
action(async()=>{try{await openAccount();}catch(error){showAuth();if(!error.message.includes('Entre na sua conta'))throw error;}});

// Never restore account content from the browser back/forward cache.
window.addEventListener('pagehide',()=>{$('#practice-panel').hidden=true;$('#onboarding-panel').hidden=true;$('#password').value='';});
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
