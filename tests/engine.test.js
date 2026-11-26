const test=require('node:test'),assert=require('node:assert/strict');const E=require('../engine.js');const cases=require('../fixtures.js');
test('punctuation normalization',()=>assert.equal(E.normalize('Hello, WORLD!'),'hello world'));
test('identical answers have F1 one',()=>assert.equal(E.f1('one two','one two'),1));
test('F1 counts duplicate words correctly',()=>assert.equal(E.f1('a a b','a b b'),2/3));
test('empty references',()=>{assert.equal(E.f1('',''),1);assert.equal(E.f1('word',''),0)});
test('wrong number fails required phrase',()=>assert.equal(E.assess('within 30 days','within 60 days',['30 days'],0).passed,false));
test('detects regressions',()=>assert.equal(E.compare(cases).regressions,2));
test('invalid case shape rejected',()=>assert.throws(()=>E.validateCases([{id:'a'}])));
test('threshold outside bounds rejected',()=>assert.throws(()=>E.compare(cases,1.5)));
test('duplicate IDs rejected',()=>assert.throws(()=>E.validateCases([cases[0],cases[0]])));
test('happy path uses four steps',async()=>{const r=await E.runWorkflow({delay:0});assert.equal(r.status,'completed');assert.equal(r.calls,4)});
test('transient error retries once',async()=>{const r=await E.runWorkflow({scenario:'retry',delay:0});assert.equal(r.status,'completed');assert.equal(r.calls,5);assert.equal(r.trace.filter(e=>e.status==='retry_scheduled').length,1)});
test('missing order stops before shipment',async()=>{const r=await E.runWorkflow({scenario:'missing',delay:0});assert.equal(r.status,'no_evidence');assert.equal(r.calls,2);assert.ok(!r.trace.some(e=>e.step==='Look up shipment'))});
test('budget bounds work',async()=>{const r=await E.runWorkflow({budget:2,delay:0});assert.equal(r.status,'budget_exhausted');assert.equal(r.calls,2);assert.equal(r.answer,null)});
test('pre-cancelled run performs no calls',async()=>{const c=new AbortController();c.abort();const r=await E.runWorkflow({signal:c.signal,delay:0});assert.equal(r.status,'cancelled');assert.equal(r.calls,0)});
test('cancel during active step',async()=>{const c=new AbortController();const r=await E.runWorkflow({signal:c.signal,delay:1,onEvent:e=>{if(e.status==='running')c.abort()}});assert.equal(r.status,'cancelled');assert.equal(r.calls,1)});
test('invalid budgets rejected',async()=>assert.rejects(E.runWorkflow({budget:0})));

test('a required phrase must contain searchable text', () => {
  const testCase = {
    id: 'case-phrase',
    question: 'Question',
    expected: 'expected response',
    answerA: 'expected response',
    answerB: 'expected response',
    required: ['...'],
  };
  assert.throws(() => E.compare([testCase]), /letters or digits/);
});
