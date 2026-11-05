'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function fixture(mode='sandbox',failDraw=false,losing=false){
  const ids=['coupon-open','coupon-dialog','coupon-spin','coupon-wheel','coupon-result','coupon-rules','coupon-consent','coupon-accept','coupon-outcomes','coupon-title','coupon-close','coupon-plans'];
  const elements=Object.fromEntries(ids.map(id=>['#'+id,{hidden:true,disabled:false,checked:false,textContent:'',style:{},listeners:{},addEventListener(event,fn){this.listeners[event]=fn;},replaceChildren(...children){this.children=children;},showModal(){this.open=true;},close(){this.open=false;}}]));
  const calls=[];
  const rules={id:'campaign-v1',valid_seconds:600,ends_at:2000000000,products:['essencial'],max_uses:5,outcomes:[{discount_bps:1700,weight:1,total_weight:1}],notice:'Sandbox only'};
  if(losing)Object.assign(rules,{valid_months:3,valid_seconds:null,products:['avancado'],outcomes:[{discount_bps:500,weight:1,total_weight:100},{discount_bps:0,weight:99,total_weight:100}]});
  const fetch=async(path,options)=>{calls.push({path,options});let data;
    if(path==='/api/coupon-experience')data={mode,rules:mode==='sandbox'?rules:null};
    else if(path==='/api/auth/me')data={csrf:'test-csrf'};
    else if(path==='/api/sandbox/coupons/draw'){
      if(failDraw)return {ok:false,status:503,json:async()=>({detail:'Campanha indisponível'})};
      data=losing?{won:false,code:null,discount_bps:0,expires_at:2000000000}:{code:'TEST-SERVER-RESULT',discount_bps:1700,expires_at:2000000000};
    }else throw Error('Unexpected endpoint');
    return {ok:true,status:200,json:async()=>data};
  };
  const context={document:{querySelector:s=>elements[s],createElement:()=>({textContent:''})},fetch,window:{matchMedia:()=>({matches:true}),setTimeout:fn=>fn()},Math:mode==='sandbox'?{random(){throw Error('Client cannot draw a sandbox outcome');},floor:Math.floor}:Math,Date,Error};
  vm.runInNewContext(fs.readFileSync('web/coupon-demo.js','utf8'),context);
  return {elements,calls,async open(){elements['#coupon-open'].listeners.click();await new Promise(resolve=>setImmediate(resolve));},async spin(){await elements['#coupon-spin'].listeners.click();}};
}
test('sandbox wheel displays server result, requires rules and disables repeat',async()=>{
  const f=fixture();await f.open();
  assert.equal(f.elements['#coupon-spin'].disabled,true);
  f.elements['#coupon-accept'].checked=true;f.elements['#coupon-accept'].listeners.change();
  await f.spin();
  assert.match(f.elements['#coupon-result'].textContent,/TEST-SERVER-RESULT/);
  assert.match(f.elements['#coupon-result'].textContent,/17%/);
  assert.equal(f.elements['#coupon-spin'].disabled,true);
  const call=f.calls.find(c=>c.path.endsWith('/draw'));
  assert.deepEqual(JSON.parse(call.options.body),{campaign:'campaign-v1',accepted_rules:true});
  assert.equal(call.options.headers['X-CSRF-Token'],'test-csrf');
});
test('failed server draw never invents or displays a coupon',async()=>{
  const f=fixture('sandbox',true);await f.open();
  f.elements['#coupon-accept'].checked=true;f.elements['#coupon-accept'].listeners.change();await f.spin();
  assert.equal(f.elements['#coupon-result'].textContent,'Campanha indisponível');
  assert.equal(f.elements['#coupon-spin'].disabled,false);
  assert.equal(f.elements['#coupon-wheel'].style.transform,undefined);
});
test('demonstration spins without requesting an account or coupon',async()=>{
  const f=fixture('demonstration');await f.open();await f.spin();
  assert.match(f.elements['#coupon-result'].textContent,/Nenhum cupom foi emitido/);
  assert.equal(f.calls.length,1);
});

test('approved losing outcome displays no prize and calendar-month rules',async()=>{
  const f=fixture('sandbox',false,true);await f.open();
  assert.match(f.elements['#coupon-rules'].textContent,/3 meses corridos/);
  assert.match(f.elements['#coupon-rules'].textContent,/Avançado/);
  assert.match(f.elements['#coupon-outcomes'].children[0].textContent,/5%.*1 em 100/);
  assert.match(f.elements['#coupon-outcomes'].children[1].textContent,/Sem prêmio.*99 em 100/);
  f.elements['#coupon-accept'].checked=true;f.elements['#coupon-accept'].listeners.change();await f.spin();
  assert.match(f.elements['#coupon-result'].textContent,/não houve prêmio/);
  assert.doesNotMatch(f.elements['#coupon-result'].textContent,/Cupom sandbox:|null/);
  assert.equal(f.elements['#coupon-spin'].disabled,true);
});
