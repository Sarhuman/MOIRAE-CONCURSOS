"use strict";
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function fixture({verified=true,completed=false,authenticated=false}={}){
 const nodes=new Map();let focused=null,logged=authenticated;
 function node(id){if(!nodes.has(id))nodes.set(id,{id,hidden:false,disabled:false,checked:false,value:'',textContent:'',listeners:{},classList:{toggle(){}},setAttribute(k,v){this[k]=v;},addEventListener(k,v){this.listeners[k]=v;},replaceChildren(...children){this.children=children;},append(){},focus(){focused=id;}});return nodes.get(id);}
 const quota={plan:'free',limit:30,remaining:30,used:0,unlimited:false};
 const active={id:'session',status:'active',total:5,answered:0,quota,question:{id:'q1',area:'Matemática',subject:'Razão',source:'Autoral',prompt:'Uma pergunta',options:[{id:'a',text:'Opção A'}]}};
 const finished={status:'completed',total:5,answered:5,summary:{correct:4,total:5},quota};
 const document={querySelector:node,querySelectorAll:()=>[...nodes.values()],createElement:()=>({append(){},textContent:''}),createTextNode:text=>text};
 const fetch=async path=>{let data;if(path==='/api/auth/me'){if(!logged)return{ok:false,status:401,json:async()=>({detail:'Entre na sua conta'})};data={csrf:'synthetic',email_verified:verified,policy_accepted:true};}
 else if(path==='/api/auth/login'){logged=true;data={csrf:'synthetic'};}
 else if(path==='/api/auth/logout'){logged=false;data={};}
 else if(path==='/api/practice/current')data={quota,session:null,completed:completed?finished:null};
 else if(path==='/api/practice/start')data=active;
 else throw Error('Unexpected request '+path);
 return{ok:true,status:200,json:async()=>data};};
 const context={document,fetch,window:{addEventListener(){}},location:{search:''},URLSearchParams,Error};
 vm.runInNewContext(fs.readFileSync('web/study.js','utf8'),context);
 const flush=()=>new Promise(resolve=>setImmediate(resolve));
 return{node,flush,get focus(){return focused;},async click(id){await node(id).listeners.click();await flush();},async login(){node('#email').value='fixture@example.test';node('#password').value='test-password-only';node('#auth-form').listeners.submit({preventDefault(){}});await flush();}};
}
test('initial restoration does not steal focus; explicit login and logout have visible destinations',async()=>{
 const f=fixture();await f.flush();assert.equal(f.focus,null);await f.login();assert.equal(f.focus,'#member-title');assert.equal(f.node('#auth-panel').hidden,true);await f.click('#logout');assert.equal(f.focus,'#email');assert.equal(f.node('#practice-panel').hidden,true);
});
test('pending account focuses confirmation guidance instead of a hidden submit',async()=>{
 const f=fixture({verified:false});await f.flush();await f.login();assert.equal(f.focus,'#onboarding-title');assert.equal(f.node('#onboarding-panel').hidden,false);assert.equal(f.node('#practice-panel').hidden,true);
});
test('start and next question move keyboard focus to the new question',async()=>{
 const f=fixture({authenticated:true});await f.flush();assert.equal(f.focus,null);await f.click('#start');assert.equal(f.focus,'#question-title');f.node('#next').focus();await f.click('#next');assert.equal(f.focus,'#question-title');assert.equal(f.node('#choices').disabled,false);
});
test('restoring a finished activity on explicit login focuses its result, not question one',async()=>{
 const f=fixture({completed:true});await f.flush();await f.login();assert.equal(f.focus,'#complete');assert.equal(f.node('#question-panel').hidden,true);assert.match(f.node('#summary').textContent,/4 de 5/);
});

test('account initial load does not steal focus; explicit recovery focuses its message',async()=>{
 const nodes=new Map();let focused=null;
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',listeners:{},addEventListener(k,v){this.listeners[k]=v;},focus(){focused=id;}});return nodes.get(id);};
 const context={document:{querySelector:node,querySelectorAll:()=>[]},window:{addEventListener(){}},location:{hash:'',pathname:'/conta'},URLSearchParams,
 fetch:async path=>({ok:path!=='/api/auth/me',json:async()=>path==='/api/auth/me'?{detail:'Entre na sua conta'}:{message:'Instruções preparadas.'}})};
 vm.runInNewContext(fs.readFileSync('web/account.js','utf8'),context);
 await new Promise(resolve=>setImmediate(resolve));assert.equal(focused,null);
 node('#reset-email').value='fixture@example.test';node('#request-reset-form').listeners.submit({preventDefault(){}});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(focused,'#account-status');assert.equal(node('#account-status').textContent,'Instruções preparadas.');
});
