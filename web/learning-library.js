'use strict';
(() => {
  const $=s=>document.querySelector(s);
  const el=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
  let data=null,track=null,index=0,storageKey=null,done=new Set(),loadVersion=0;
  function save(){try{localStorage.setItem(storageKey,JSON.stringify([...done]));}catch{$('#library-notice').textContent='Não foi possível salvar o progresso neste navegador. Você pode continuar lendo.';}}
  function clearContent(){
    loadVersion++;
    data=track=null;storageKey=null;done=new Set();
    $('#library-content').hidden=true;$('#library-reader').hidden=true;
    for(const id of ['#library-filter','#library-lessons','#library-options'])$(id).replaceChildren();
    for(const id of ['#library-track','#library-title','#library-concept','#library-example','#library-question','#library-feedback','#library-progress'])$(id).textContent='';
  }
  function menu(){
    document.querySelectorAll('[data-track]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.track===track.id)));
    $('#library-lessons').replaceChildren(...track.lessons.map((lesson,i)=>{
      const li=el('li',''),b=el('button',(done.has(lesson.id)?'✓ ':'')+lesson.title);b.type='button';
      if(i===index)b.setAttribute('aria-current','step');b.onclick=()=>{index=i;render(true);};li.append(b);return li;
    }));
    $('#library-progress').textContent=`${track.lessons.filter(l=>done.has(l.id)).length} de ${track.lessons.length} exercícios acertados nesta trilha.`;
  }
  function render(focus=false){
    const lesson=track.lessons[index];menu();$('#library-reader').hidden=false;
    $('#library-track').textContent=track.title;$('#library-title').textContent=lesson.title;
    $('#library-concept').textContent=lesson.concept;$('#library-example').textContent=lesson.example;
    $('#library-question').textContent=lesson.question;
    $('#library-options').replaceChildren(...lesson.options.map((text,i)=>{const label=el('label',''),input=document.createElement('input');input.type='radio';input.name='option';input.value=String(i);input.required=true;label.append(input,document.createTextNode(text));return label;}));
    $('#library-feedback').hidden=true;$('#library-next').hidden=index===track.lessons.length-1;
    if(focus)$('#library-reader').focus();
  }
  $('#library-exercise').onsubmit=e=>{
    e.preventDefault();if(!track)return;const lesson=track.lessons[index],choice=new FormData(e.currentTarget).get('option');if(choice===null)return;
    const correct=Number(choice)===lesson.answer;if(correct){done.add(lesson.id);save();menu();}
    $('#library-feedback').hidden=false;$('#library-feedback').textContent=(correct?'Raciocínio correto. ':'Vamos revisar. ')+lesson.explanation;
  };
  $('#library-next').onclick=()=>{if(track&&index<track.lessons.length-1){index++;render(true);}};
  $('#library-clear').onclick=()=>{if(!track||!confirm('Limpar somente o progresso desta conta neste navegador?'))return;done.clear();save();render();};
  async function load(){
    clearContent();$('#library-access').hidden=false;
    const version=loadVersion;
    $('#library-notice').textContent='Conferindo seu acesso…';
    try{
      const response=await fetch('/api/learning-library',{credentials:'same-origin',cache:'no-store'});
      if(version!==loadVersion)return;
      if(response.status===401||response.status===403){
        $('#library-notice').textContent=response.status===401?'Entre ou crie sua conta gratuita para acessar as lições e questões. Não é necessário assinar.':'Confirme seu e-mail e os termos do piloto na área Minha conta antes de acessar as questões.';
        $('#library-enter').href=response.status===403?'/conta':'/estudar';return;
      }
      if(!response.ok)throw Error('Não foi possível carregar as trilhas. Atualize a página.');
      const loaded=await response.json();if(version!==loadVersion)return;
      data=loaded;storageKey='moirae-library-v2:'+data.progress_key;
      try{const values=JSON.parse(localStorage.getItem(storageKey)||'[]');if(Array.isArray(values))done=new Set(values.filter(v=>typeof v==='string'));}catch{}
      $('#library-notice').textContent=data.notice;$('#library-access').hidden=true;$('#library-content').hidden=false;
      $('#library-filter').replaceChildren(...data.tracks.map(t=>{const b=el('button',t.title);b.type='button';b.dataset.track=t.id;b.setAttribute('aria-pressed','false');b.onclick=()=>{track=t;index=0;render(true);};return b;}));
      track=data.tracks.find(t=>t.id===new URLSearchParams(location.search).get('trilha'))||data.tracks[0];index=0;render();
    }catch(e){if(version!==loadVersion)return;clearContent();$('#library-notice').textContent=e.message;}
  }
  window.addEventListener('pagehide',clearContent);
  window.addEventListener('pageshow',e=>{if(e.persisted)load();});
  load();
})();
