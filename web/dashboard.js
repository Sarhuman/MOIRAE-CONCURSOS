'use strict';
(async()=>{const $=s=>document.querySelector(s);try{
const r=await fetch('/api/dashboard',{credentials:'same-origin'}),d=await r.json();if(!r.ok)throw new Error(d.detail||'Não foi possível consultar o painel.');
$('#dashboard-status').textContent=d.notice;$('#dashboard-data').hidden=false;
$('#dashboard-total').textContent=d.answered?`${d.answered} questões respondidas · ${d.correct} acertos · ${d.accuracy}% de acerto.`:'Você ainda não respondeu questões de prática.';
const focus=learningFocus(d.areas);
$('#focus-title').textContent=!focus?'Seu primeiro passo começa com uma sessão.':focus.errors?`Volte a ${focus.area}.`:'Continue ampliando sua prática.';
$('#focus-description').textContent=!focus?'Escolha 15 minutos acima. Suas respostas vão ajudar a organizar as próximas revisões.':focus.errors?`${focus.errors} respostas incorretas em ${focus.answered} tentativas nesta área. Abra o caderno para entender os erros antes de repetir.`:'Você acertou todas as questões registradas. Experimente novos conteúdos e retome as revisões quando vencerem.';
$('#focus-sample').textContent=focus&&focus.answered<10?'Amostra inicial: poucos exercícios ainda não permitem concluir domínio da área.':'O foco considera erros acumulados de prática; não estima nota, TRI ou domínio de todo o conteúdo.';
$('#dashboard-areas').replaceChildren(...Object.entries(d.areas).map(([area,value])=>{const article=document.createElement('article'),h=document.createElement('h3'),p=document.createElement('p'),meter=document.createElement('meter'),note=document.createElement('p');h.textContent=area;p.textContent=`${value.correct} acertos em ${value.answered} respostas`;meter.min=0;meter.max=Math.max(1,value.answered);meter.value=value.correct;meter.setAttribute('aria-label',area+': '+p.textContent);note.className='note';note.textContent=value.answered<10?'Amostra inicial · continue praticando':'Percentual das tentativas registradas';article.append(h,p,meter,note);return article;}));
$('#dashboard-recent').replaceChildren(...d.recent_attempts.map(value=>{const li=document.createElement('li');li.textContent=`${value.day} · ${value.question_id} · ${value.correct?'acertou':'errou'}`;return li;}));$('#dashboard-mocks').textContent=`Simulados encerrados: ${d.completed_mock_exams}.`;
}catch(e){$('#dashboard-status').textContent=e.message;}})();
