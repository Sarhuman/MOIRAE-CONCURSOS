const {test}=require('node:test');
const assert=require('node:assert/strict');
const {learningFocus}=require('../web/learning-focus');
test('empty history does not invent a weak area',()=>assert.equal(learningFocus({Matemática:{answered:0,correct:0}}),null));
test('focus prioritizes accumulated errors and preserves sample size',()=>{const result=learningFocus({Humanas:{answered:2,correct:0},Matemática:{answered:10,correct:6}});assert.equal(result.area,'Matemática');assert.equal(result.errors,4);assert.equal(result.answered,10);});
test('equal errors prioritize lower accuracy',()=>assert.equal(learningFocus({Humanas:{answered:4,correct:3},Natureza:{answered:2,correct:1}}).area,'Natureza'));
