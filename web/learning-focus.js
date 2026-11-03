'use strict';
function learningFocus(areas){
  const rows=Object.entries(areas).filter(([,v])=>v.answered>0).map(([area,v])=>({area,answered:v.answered,correct:v.correct,errors:v.answered-v.correct,accuracy:Math.round(100*v.correct/v.answered)}));
  rows.sort((a,b)=>b.errors-a.errors||a.accuracy-b.accuracy||a.area.localeCompare(b.area));
  return rows[0]||null;
}
if(typeof module!=='undefined')module.exports={learningFocus};
