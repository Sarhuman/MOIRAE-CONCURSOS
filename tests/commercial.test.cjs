const test=require('node:test'),assert=require('node:assert/strict');
const {quote}=require('../web/portfolio-offers.js');const data=require('../web/portfolio-offers.json');
test('product markup is applied once and installment parts sum to estimate',()=>{const q=quote(data,'essencial',12,12);assert.equal(q.total,44880);assert.equal(q.rate,1728);assert.equal(q.extra,7756);assert.equal(q.estimate,52636);assert.equal(q.parts.reduce((a,b)=>a+b,0),q.estimate);assert.equal(q.credits,10);});
test('credit package and monthly calculations keep no-financing totals',()=>{assert.equal(quote(data,'avancado',1,1).total,11000);assert.equal(quote(data,'creditos-10',1,1).total,4950);assert.equal(quote(data,'creditos-30',1,3).parts.length,3);});
test('unknown products and unsupported durations/installments fail',()=>{assert.throws(()=>quote(data,'fake',1,1));assert.throws(()=>quote(data,'essencial',2,1));assert.throws(()=>quote(data,'creditos-5',1,2));});
