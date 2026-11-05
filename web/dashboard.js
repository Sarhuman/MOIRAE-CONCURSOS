'use strict';
(async()=>{const $=s=>document.querySelector(s);try{
function access(title,description,primary,href,benefits){
  $('#dashboard-access').hidden=false;$('#dashboard-access-title').textContent=title;$('#dashboard-access-description').textContent=description;$('#dashboard-access-primary').textContent=primary;$('#dashboard-access-primary').href=href;
  $('#dashboard-access-benefits').replaceChildren(...benefits.map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
}
const response=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});
if(response.status===401){access('Seu painel começa com uma conta.','Crie sua conta Free ou entre. As questões gratuitas também exigem cadastro.','Entrar ou criar conta','/estudar',['Free: 30 questões de prática por mês, biblioteca e acervo.','Painel e planejamento exigem acesso pago de teste.']);$('#dashboard-status').textContent='Entre para conferir seu acesso.';return;}
if(!response.ok)throw Error('Não foi possível conferir seu acesso. Atualize a página.');
const me=await response.json();
if(!me.email_verified||!me.policy_accepted){access('Conclua a confirmação da sua conta.','Suas questões ficam disponíveis após confirmar o e-mail e as políticas do piloto.','Abrir Minha conta','/conta',['O cadastro Free não exige contratação.']);$('#dashboard-status').textContent='Confirmação pendente.';return;}
if(me.plan==='free'){access('Seu Free continua disponível.','O painel de desempenho e as sessões planejadas são recursos de acesso pago ativo. Você pode seguir estudando sem assinar.','Continuar no Free','/estudar',['30 questões mensais compartilhadas com simulados.','Diagnóstico inicial, explicações e último resultado.','Biblioteca introdutória e acervo após login.']);$('#dashboard-status').textContent='Conta Free · painel pago não liberado.';return;}
const r=await fetch('/api/dashboard' ,{credentials:'same-origin'}),d=await r.json();if(!r.ok)throw new Error(d.detail||'Não foi possível consultar o painel.');
$('#dashboard-status').textContent=d.notice;$('#dashboard-data').hidden=false;$('#dashboard-paid-actions').hidden=false;
$('#dashboard-total').textContent=d.answered?`${d.answered} questões respondidas · ${d.correct} acertos · ${d.accuracy}% de acerto.`:'Você ainda não respondeu questões de prática.';
const focus=learningFocus(d.areas);
$('#focus-title').textContent=!focus?'Seu primeiro passo começa com uma sessão.':focus.errors?`Volte a ${focus.area}.`:'Continue ampliando sua prática.';
$('#focus-description').textContent=!focus?'Escolha 15 minutos acima. Suas respostas vão ajudar a organizar as próximas revisões.':focus.errors?`${focus.errors} respostas incorretas em ${focus.answered} tentativas nesta área. Abra o caderno para entender os erros antes de repetir.`:'Você acertou todas as questões registradas. Experimente novos conteúdos e retome as revisões quando vencerem.';
$('#focus-sample').textContent=focus&&focus.answered<10?'Amostra inicial: poucos exercícios ainda não permitem concluir domínio da área.':'O foco considera erros acumulados de prática; não estima nota, TRI ou domínio de todo o conteúdo.';
$('#dashboard-areas').replaceChildren(...Object.entries(d.areas).map(([area,value])=>{const article=document.createElement('article'),h=document.createElement('h3'),p=document.createElement('p'),meter=document.createElement('meter'),note=document.createElement('p');h.textContent=area;p.textContent=`${value.correct} acertos em ${value.answered} respostas`;meter.min=0;meter.max=Math.max(1,value.answered);meter.value=value.correct;meter.setAttribute('aria-label',area+': '+p.textContent);note.className='note';note.textContent=value.answered<10?'Amostra inicial · continue praticando':'Percentual das tentativas registradas';article.append(h,p,meter,note);return article;}));
$('#dashboard-recent').replaceChildren(...d.recent_attempts.map(value=>{const li=document.createElement('li');li.textContent=`${value.day} · ${value.question_id} · ${value.correct?'acertou':'errou'}`;return li;}));$('#dashboard-mocks').textContent=`Simulados encerrados: ${d.completed_mock_exams}.`;
}catch(e){$('#dashboard-status').textContent=e.message;}})();

// Never restore account content from the browser back/forward cache.
window.addEventListener('pagehide',()=>{document.querySelector('#dashboard-data').hidden=true;document.querySelector('#planner-panel').hidden=true;document.querySelector('#dashboard-paid-actions').hidden=true;});
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
