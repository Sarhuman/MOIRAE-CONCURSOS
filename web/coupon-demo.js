'use strict';
(() => {
  const $=s=>document.querySelector(s),open=$('#coupon-open'),dialog=$('#coupon-dialog');
  if(!open||!dialog||typeof dialog.showModal!=='function')return;
  const spin=$('#coupon-spin'),wheel=$('#coupon-wheel'),result=$('#coupon-result'),rules=$('#coupon-rules');
  const consent=$('#coupon-consent'),accept=$('#coupon-accept'),list=$('#coupon-outcomes');
  let rotation=0,mode='demonstration',campaign=null,busy=false,ready=false,drawn=false;
  async function api(path,body,csrf){
    const r=await fetch(path,{credentials:'same-origin',cache:'no-store',headers:body?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},...(body?{method:'POST',body:JSON.stringify(body)}:{})});
    let d;try{d=await r.json();}catch{throw Error('Não foi possível consultar a campanha. Tente novamente.');}
    if(!r.ok)throw Error(r.status===401?'Entre na sua conta de teste para participar.':d.detail||'Campanha indisponível.');return d;
  }
  function availability(){spin.disabled=busy||!ready||(mode==='sandbox'&&(!accept.checked||drawn));}
  async function configure(){
    ready=false;availability();result.textContent='Consultando a experiência…';
    try{
      const d=await api('/api/coupon-experience');mode=d.mode;campaign=d.rules;
      if(mode==='sandbox'&&campaign){
        $('#coupon-title').textContent='Um giro de teste. Um resultado do servidor.';
        const validity=campaign.valid_months?`${campaign.valid_months} meses corridos a partir do giro (calendário de Brasília)`: `até ${Math.floor(campaign.valid_seconds/60)} minutos, limitado ao fim da campanha`;
        const products=campaign.products.map(p=>({avancado:'Avançado',essencial:'Essencial'})[p]||p).join(', ');
        rules.textContent=`Campanha sandbox ${campaign.id}. Uma participação por conta; cupom válido por ${validity}. Produtos elegíveis: ${products}. Rodadas até ${new Date(campaign.ends_at*1000).toLocaleString('pt-BR')}. Limite global: ${campaign.max_uses} usos. Sem compra ou desconto real.`;
        list.replaceChildren(...campaign.outcomes.map(o=>{const li=document.createElement('li');li.textContent=o.discount_bps>0?`${o.discount_bps/100}% de desconto de teste · chance ${o.weight} em ${o.total_weight}.`:`Sem prêmio · chance ${o.weight} em ${o.total_weight}.`;return li;}));
        consent.hidden=false;list.hidden=false;spin.textContent='Solicitar giro sandbox';
        result.textContent=campaign.notice;
      }else{
        rules.textContent='Esta roleta é uma prévia visual. Não concede desconto, crédito ou prêmio. A campanha comercial ainda não está ativa e não há coleta de e-mail.';
        consent.hidden=true;list.hidden=true;spin.textContent='Testar o giro demonstrativo';
        result.textContent='Você pode testar a animação sem cadastro.';
      }
      ready=true;
    }catch(e){
      mode='demonstration';campaign=null;ready=true;
      consent.hidden=true;list.hidden=true;spin.textContent='Testar apenas a animação';
      rules.textContent='Campanha não consultada. Somente demonstração visual, sem cupom, desconto ou prêmio.';
      result.textContent='O servidor da campanha está indisponível. Você pode testar somente a animação.';
    }
    availability();
  }
  open.hidden=false;
  open.addEventListener('click',()=>{dialog.showModal();if(!ready)configure();});
  $('#coupon-close').addEventListener('click',()=>dialog.close());
  $('#coupon-plans').addEventListener('click',()=>dialog.close());
  accept.addEventListener('change',availability);
  spin.addEventListener('click',async()=>{
    if(busy||!ready)return;
    busy=true;availability();result.textContent='Preparando o giro…';
    try{
      let message,angle;
      if(mode==='sandbox'){
        if(!accept.checked)throw Error('Leia e aceite as regras de teste antes de girar.');
        const me=await api('/api/auth/me');
        const d=await api('/api/sandbox/coupons/draw',{campaign:campaign.id,accepted_rules:true},me.csrf);
        angle=(10000-d.discount_bps)/10000*360;
        message=d.won===false||d.discount_bps===0?'Desta vez não houve prêmio. Nenhum cupom foi emitido. Esta participação já foi registrada; atualizar a página não concede outro giro.':`Cupom sandbox: ${d.code}. Desconto de teste: ${d.discount_bps/100}%. Validade: ${new Date(d.expires_at*1000).toLocaleString('pt-BR')}. Uso único, sem valor comercial; não aplicado a compras. Repetir a solicitação retorna o mesmo resultado.`;
        drawn=true;
      }else{
        angle=Math.floor(Math.random()*360);
        message='Demonstração concluída. Nenhum cupom foi emitido e nenhum preço foi alterado.';
      }
      const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const finish=()=>{result.textContent=message;spin.textContent=mode==='sandbox'?'Resultado recebido':'Testar novamente';busy=false;availability();};
      if(reduced){finish();}else{rotation+=1800+angle;wheel.style.transform=`rotate(${rotation}deg)`;window.setTimeout(finish,1850);}
    }catch(e){result.textContent=e.message;busy=false;availability();}
  });
})();
