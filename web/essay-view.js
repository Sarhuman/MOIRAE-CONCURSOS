'use strict';
(function(root){
  const states={received:'Recebido · crédito de teste reservado',processing:'Preparando a demonstração',completed:'Demonstração concluída',failed:'Não foi possível concluir · reserva liberada'};
  function segments(text,annotations){
    const valid=annotations.filter(a=>Number.isInteger(a.start)&&Number.isInteger(a.end)&&a.start>=0&&a.end>a.start&&a.end<=text.length&&text.slice(a.start,a.end)===a.quote);
    const points=[...new Set([0,text.length,...valid.flatMap(a=>[a.start,a.end])])].sort((a,b)=>a-b);
    return points.slice(0,-1).map((start,i)=>({text:text.slice(start,points[i+1]),annotations:valid.filter(a=>a.start<=start&&a.end>=points[i+1])}));
  }
  const api={states,segments};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EssayView=api;
})(typeof globalThis==='undefined'?this:globalThis);
