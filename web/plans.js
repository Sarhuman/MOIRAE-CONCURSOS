'use strict';
const $=selector=>document.querySelector(selector);
let csrf='',chosen=null,key='',orderId='',busy=false;
const money=cents=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(cents/100);
async function api(path,body){const r=await fetch('/api'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(body===undefined?{}:{body:JSON.stringify(body)})});const d=await r.json();if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:'Não foi possível concluir.');return d;}
async function act(work){if(busy)return;busy=true;try{await work();}catch(e){$('#billing-status').textContent=e.message;}finally{busy=false;}}
async function load(){
  const catalog=await api('/billing/plans');
  $('#billing-plans').replaceChildren(...catalog.plans.map(plan=>{const article=document.createElement('article'),h=document.createElement('h2'),p=document.createElement('p'),credits=document.createElement('p'),button=document.createElement('button');h.textContent=plan.name;p.textContent=money(plan.price_cents)+' por '+plan.days+' dias';credits.textContent=plan.essay_credits+' créditos previstos de redação por IA. Questões sem cota e painel básico no piloto de teste. Sem videoaulas. Correção real por IA ainda indisponível.';button.type='button';button.className='button';button.textContent=catalog.checkout_enabled?'Testar compra':'Checkout em preparação';button.disabled=!catalog.checkout_enabled;button.addEventListener('click',()=>{chosen=plan;key=crypto.randomUUID();$('#checkout-description').textContent=`${plan.name} · ${money(plan.price_cents)} · 30 dias · sem renovação automática.`;$('#checkout-confirm').showModal();});article.append(h,p,credits,button);return article;}));
  if(!catalog.checkout_enabled)$('#billing-status').textContent='Checkout desabilitado. Nenhuma cobrança pode ser iniciada.';
  try{const me=await api('/auth/me');csrf=me.csrf;const current=await api('/billing/current');$('#current-access').textContent=current.access.active?`Plano ${current.access.plan} ativo até ${new Date(current.access.ends_at*1000).toLocaleString('pt-BR')}.`:'Sua conta está no Free.';
    $('#billing-orders').replaceChildren(...current.orders.map(order=>{const row=document.createElement('article'),p=document.createElement('p'),button=document.createElement('button');p.textContent=`${order.plan_id} · ${money(order.amount_cents)} · situação: ${order.status}`;button.type='button';button.textContent=order.refund_requested_at?'Solicitação já registrada':'Solicitar cancelamento ou análise';button.disabled=Boolean(order.refund_requested_at);button.addEventListener('click',()=>{orderId=order.id;$('#refund-dialog').showModal();});row.append(p,button);return row;}));
  }catch{/* Visitantes podem conhecer os preços sem consultar contas. */}
}
$('#checkout-cancel').addEventListener('click',()=>$('#checkout-confirm').close());
$('#checkout-go').addEventListener('click',()=>act(async()=>{if(!csrf)throw new Error('Entre e confirme seu e-mail antes de continuar.');const result=await api('/billing/checkout',{plan:chosen.id,key});if(result.mode!=='sandbox')throw new Error('Ambiente de pagamento inesperado.');location.assign(result.checkout_url);}));
$('#refund-cancel').addEventListener('click',()=>$('#refund-dialog').close());
$('#refund-form').addEventListener('submit',event=>{event.preventDefault();act(async()=>{const result=await api(`/billing/orders/${orderId}/refund-request`,{password:$('#refund-password').value});$('#refund-password').value='';$('#refund-dialog').close();await load();$('#billing-status').textContent=result.message;});});
act(load);

