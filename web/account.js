'use strict';
const $=selector=>document.querySelector(selector);
let csrf='',token=new URLSearchParams(location.hash.slice(1)).get('token')||'';
if(location.hash)history.replaceState(null,'',location.pathname);
let busy=false;
function say(text){$('#account-status').textContent=text;}
async function request(path,body){
  const r=await fetch('/api'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const value=await r.json();if(!r.ok)throw new Error(typeof value.detail==='string'?value.detail:'Confira os dados e tente novamente.');return value;
}
async function act(work){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{await work();}catch(e){say(e.message||'Não foi possível concluir. Tente novamente.');}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);}}
async function profile(){
  const me=await request('/auth/me');csrf=me.csrf;$('#profile-panel').hidden=false;
  const names={free:'Free',essencial:'Essencial',avancado:'Avançado'};$('#account-plan').textContent='Conta '+(names[me.plan]||'Free')+(me.plan==='free'?'':' · acesso de teste');$('#account-access-copy').textContent=!me.email_verified||!me.policy_accepted?'Conclua a confirmação desta conta para liberar questões e biblioteca. O cadastro não exige assinatura.':me.plan==='free'?'Você pode estudar sem assinar: 30 questões mensais de prática, biblioteca e acervo. Painel, revisão e planejamento exigem acesso pago ativo.':'Seu acesso ativo inclui questões sem cota, painel, erros/favoritos e planejamento. Correção real por IA e vendas continuam desativadas.';$('#profile-email').textContent=me.email;$('#verification-state').textContent=me.email_verified?'E-mail confirmado.':'Seu e-mail ainda precisa de confirmação.';
  $('#resend').hidden=me.email_verified;$('#accept-panel').hidden=me.policy_accepted;
}
$('#verify-panel').hidden=!(token&&location.pathname==='/verificar-email');
$('#reset-panel').hidden=!(token&&location.pathname==='/recuperar-senha');
$('#verify-email').addEventListener('click',()=>act(async()=>{await request('/auth/verify-email',{token});token='';$('#verify-panel').hidden=true;say('E-mail confirmado. Você já pode voltar à área de estudo.');try{await profile();}catch{/* Confirmação pode ocorrer sem sessão autenticada. */}}));
$('#reset-form').addEventListener('submit',event=>{event.preventDefault();act(async()=>{await request('/auth/reset-password',{token,password:$('#new-password').value});token='';$('#new-password').value='';$('#reset-panel').hidden=true;$('#profile-panel').hidden=true;csrf='';say('Senha atualizada. As sessões anteriores foram encerradas. Entre novamente.');});});
$('#request-reset-form').addEventListener('submit',event=>{event.preventDefault();act(async()=>{const result=await request('/auth/request-reset',{email:$('#reset-email').value});say(result.message);});});
$('#resend').addEventListener('click',()=>act(async()=>{const result=await request('/account/resend-verification',{});say(result.message);}));
$('#accept-form').addEventListener('submit',event=>{event.preventDefault();act(async()=>{await request('/account/accept-policy',{password:$('#accept-password').value,accept_terms:$('#accept-terms').checked,adult_pilot:$('#accept-adult').checked});$('#accept-password').value='';await profile();say('Aceite registrado. Confirme seu e-mail, se ainda estiver pendente.');});});
$('#export-form').addEventListener('submit',event=>{event.preventDefault();act(async()=>{const result=await request('/account/export',{password:$('#export-password').value});$('#export-password').value='';const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='moirae-dados.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);say('Arquivo preparado para download.');});});
$('#delete-form').addEventListener('submit',event=>{event.preventDefault();act(async()=>{const result=await request('/account/delete',{password:$('#delete-password').value,confirmation:$('#delete-confirmation').value});$('#delete-password').value='';$('#profile-panel').hidden=true;csrf='';say(result.message);});});
act(async()=>{try{await profile();}catch(error){if(!token)say('Entre na área de estudo para gerenciar sua conta. A recuperação de senha também funciona sem login.');}});

// Never restore account content from the browser back/forward cache.
window.addEventListener('pagehide',()=>{$('#profile-panel').hidden=true;});
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
