import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from fastapi.testclient import TestClient
from test_review import setup,register,grant,BASE,PASSWORD
from backend.moirae.essay_jobs import EssayJobs,EssayWorker
from backend.moirae.essay_provider import OpenAIEvaluator,ProviderFailure,canonical,RUBRIC
from backend.moirae.store import Store

TEXT='🌱 A educação permite ampliar oportunidades de participação social. O acesso a bibliotecas ajuda estudantes a aprender com autonomia.'

def feedback(text=TEXT):
    return dict(competencies=[dict(id=i,score=120,explanation=f'Justificativa pedagógica de C{i}.') for i in range(1,6)],annotations=[dict(competency=3,quote='🌱 A educação',guidance='Explique a relação com o argumento.')])

class FakeEvaluator:
    model='synthetic-model'
    def __init__(self,store=None,failure=None):self.calls=0;self.store=store;self.failure=failure
    def evaluate(self,theme,text):
        self.calls+=1
        if self.store:
            # Would deadlock if the remote evaluator ran inside the queue transaction.
            with self.store.connect(write=True) as db:db.execute('INSERT OR IGNORE INTO schema_version VALUES(9)')
        if self.failure:raise self.failure
        return canonical(feedback(),text)


def queue(setup):
    app,c,uid=setup;clock=[int(time.time())]
    jobs=EssayJobs(app.state.store,True,'synthetic-model',lambda:clock[0]);fake=FakeEvaluator(app.state.store)
    return app,c,uid,clock,jobs,fake


def submit(jobs,uid,key=None):return jobs.submit(uid,key or str(uuid.uuid4()),'Educação e sociedade',TEXT)


def test_complete_job_reserves_once_and_never_calls_under_transaction(setup):
    app,c,uid,clock,jobs,fake=queue(setup);key=str(uuid.uuid4());j=submit(jobs,uid,key)
    assert submit(jobs,uid,key)==j
    assert jobs.history(uid)['remaining']==9
    worker=EssayWorker(app.state.store,fake,lambda:clock[0]);assert worker.run_once()
    assert not worker.run_once() and fake.calls==1
    result=jobs.detail(uid,j['id'])
    assert result['status']=='completed' and result['result']['annotations'][0]['end']==13
    assert jobs.history(uid)['remaining']==9
    with app.state.store.connect() as db:
        assert [r[0] for r in db.execute('SELECT event FROM essay_credit_events ORDER BY rowid')]==['reserve','consume']
    assert len(jobs.evolution(uid)['groups'][0]['items'])==1
    assert len(c.post('/api/account/export',json={'password':PASSWORD}).json()['real_essays'])==1


def test_failure_releases_and_does_not_publish_zero_scores(setup):
    app,c,uid,clock,jobs,fake=queue(setup);j=submit(jobs,uid);fake.failure=ProviderFailure('refused')
    worker=EssayWorker(app.state.store,fake,lambda:clock[0]);worker.run_once()
    assert jobs.detail(uid,j['id'])['status']=='failed'
    assert jobs.detail(uid,j['id'])['result'] is None
    assert jobs.history(uid)['remaining']==10 and jobs.evolution(uid)['groups']==[]
    worker.run_once()
    with app.state.store.connect() as db:assert db.execute("SELECT count(*) FROM essay_credit_events WHERE event='release'").fetchone()[0]==1


def test_transient_retry_is_bounded_and_releases_final_failure(setup):
    app,c,uid,clock,jobs,fake=queue(setup);j=submit(jobs,uid);fake.failure=ProviderFailure('provider_unavailable',True)
    worker=EssayWorker(app.state.store,fake,lambda:clock[0])
    assert worker.run_once() and not worker.run_once()
    assert jobs.history(uid)['remaining']==9
    clock[0]+=61;assert worker.run_once()
    clock[0]+=121;assert worker.run_once()
    assert fake.calls==3 and jobs.history(uid)['remaining']==10
    assert jobs.detail(uid,j['id'])['status']=='failed'


def test_crash_lease_recovery_and_stale_worker_cannot_settle(setup):
    app,c,uid,clock,jobs,fake=queue(setup);j=submit(jobs,uid)
    worker=EssayWorker(app.state.store,fake,lambda:clock[0]);claim=worker.claim();assert claim
    assert worker.claim() is None
    clock[0]+=121
    restarted=EssayWorker(Store(app.state.store.path),fake,lambda:clock[0]);assert restarted.run_once()
    assert jobs.detail(uid,j['id'])['status']=='completed'
    with app.state.store.connect() as db:assert db.execute('SELECT attempts FROM real_essay_jobs').fetchone()[0]==2


def test_concurrent_reservation_only_one_pending_and_cannot_overdraft(setup):
    app,c,uid,clock,jobs,fake=queue(setup)
    def send(_):
        from fastapi import HTTPException
        try:return submit(jobs,uid)['id']
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(send,range(4)))
    assert results.count(409)==3
    with app.state.store.connect() as db:
        assert db.execute('SELECT sum(delta) FROM essay_credit_events').fetchone()[0]==1
        db.execute('SELECT 1')


def test_revocation_prevents_provider_call_and_releases_credit(setup):
    app,c,uid,clock,jobs,fake=queue(setup);j=submit(jobs,uid)
    with app.state.store.connect(write=True) as db:db.execute("UPDATE access_grants SET status='revoked'")
    assert not EssayWorker(app.state.store,fake,lambda:clock[0]).run_once()
    assert fake.calls==0 and jobs.detail(uid,j['id'])['status']=='failed'


def test_daily_cap_and_worker_exclusion(setup):
    app,c,uid,clock,jobs,fake=queue(setup);submit(jobs,uid)
    worker=EssayWorker(app.state.store,fake,lambda:clock[0],daily_limit=1);worker.run_once();submit(jobs,uid)
    assert not worker.run_once() and fake.calls==1


def test_jobs_are_private_and_demo_never_appears_in_evolution(setup):
    from fastapi import HTTPException
    app,c,uid,clock,jobs,fake=queue(setup);j=submit(jobs,uid)
    other,oid=register(app,'other-real@example.test');grant(app,oid,now=clock[0])
    assert jobs.history(oid)['items']==[] and jobs.evolution(oid)['groups']==[]
    with pytest.raises(HTTPException) as e:jobs.detail(oid,j['id'])
    assert e.value.status_code==404


def test_http_feature_disabled_consent_and_csrf(setup):
    app,c,uid,clock,jobs,fake=queue(setup)
    body=dict(key=str(uuid.uuid4()),theme='Educação e sociedade',text=TEXT,accept_external=True)
    assert c.post('/api/essay-evaluations',json=body).status_code==503
    assert c.get('/api/essay-evaluations').status_code==503
    app.state.real_essays.enabled=True;app.state.real_essays.model='synthetic-model'
    assert c.post('/api/essay-evaluations',json={**body,'accept_external':False}).status_code==422
    assert c.post('/api/essay-evaluations',json=body,headers={'X-CSRF-Token':'bad'}).status_code==403
    r=c.post('/api/essay-evaluations',json=body);assert r.status_code==202
    assert c.get('/api/essay-evaluations/evolution').status_code==200


def test_provider_payload_and_literal_utf16_quote():
    seen=[]
    def handle(request):
        seen.append(request);return httpx.Response(200,json=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(feedback()))])]))
    result=OpenAIEvaluator('synthetic-key','synthetic-model',httpx.MockTransport(handle)).evaluate('Tema',TEXT)
    payload=json.loads(seen[0].content)
    assert payload['store'] is False and payload['tools']==[] and payload['max_output_tokens']==3500
    assert payload['text']['format']['strict'] is True
    assert seen[0].url=='https://api.openai.com/v1/responses'
    assert result['annotations'][0]['start']==0
    assert result['annotations'][0]['end']==len('🌱 A educação'.encode('utf-16-le'))//2


@pytest.mark.parametrize('body',[dict(status='incomplete'),dict(status='completed',output=[dict(type='message',content=[dict(type='refusal',refusal='No')])]),dict(status='completed',output=[])])
def test_provider_incomplete_refusal_and_empty_fail_safely(body):
    evaluator=OpenAIEvaluator('synthetic-key','synthetic-model',httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
    with pytest.raises(ProviderFailure):evaluator.evaluate('Tema',TEXT)


def test_provider_rejects_malformed_or_ambiguous_quote():
    data=feedback();data['competencies'][0]['id']=2
    with pytest.raises(Exception):canonical(data,TEXT)
    data=feedback();data['annotations'][0]['quote']='não está no texto'
    with pytest.raises(ProviderFailure):canonical(data,TEXT)
    data=feedback();data['annotations'][0]['quote']='a'
    with pytest.raises(ProviderFailure):canonical(data,TEXT)


def test_stale_evaluator_result_cannot_overwrite_new_lease(setup):
    app,c,uid,clock,jobs,first=queue(setup);j=submit(jobs,uid)
    second=FakeEvaluator()
    def new_result(theme,text):
        data=feedback()
        for score in data['competencies']:score['score']=160
        return canonical(data,text)
    second.evaluate=new_result
    def old_result(theme,text):
        clock[0]+=121
        assert EssayWorker(app.state.store,second,lambda:clock[0]).run_once()
        return canonical(feedback(),text)
    first.evaluate=old_result
    assert EssayWorker(app.state.store,first,lambda:clock[0]).run_once()
    result=jobs.detail(uid,j['id'])
    assert all(c['score']==160 for c in result['result']['competencies'])
    with app.state.store.connect() as db:assert db.execute("SELECT count(*) FROM essay_credit_events WHERE event='consume'").fetchone()[0]==1


def test_last_credit_cannot_be_spent_twice(setup):
    from fastapi import HTTPException
    app,c,uid,clock,jobs,fake=queue(setup)
    with app.state.store.connect(write=True) as db:db.execute('UPDATE access_grants SET essay_credits=1')
    j=submit(jobs,uid);EssayWorker(app.state.store,fake,lambda:clock[0]).run_once()
    assert jobs.history(uid)['remaining']==0
    with pytest.raises(HTTPException) as e:submit(jobs,uid)
    assert e.value.status_code==409


def test_access_revoked_during_provider_call_discards_output(setup):
    app,c,uid,clock,jobs,fake=queue(setup);j=submit(jobs,uid)
    def revoke(theme,text):
        with app.state.store.connect(write=True) as db:db.execute("UPDATE access_grants SET status='revoked'")
        return canonical(feedback(),text)
    fake.evaluate=revoke
    EssayWorker(app.state.store,fake,lambda:clock[0]).run_once()
    assert jobs.detail(uid,j['id'])['status']=='failed' and jobs.detail(uid,j['id'])['result'] is None
    with app.state.store.connect() as db:assert db.execute('SELECT sum(delta) FROM essay_credit_events').fetchone()[0]==0


def test_evolution_separates_evaluator_versions(setup):
    app,c,uid,clock,jobs,fake=queue(setup)
    submit(jobs,uid);EssayWorker(app.state.store,fake,lambda:clock[0]).run_once()
    jobs.model='synthetic-model-2';fake.model='synthetic-model-2'
    submit(jobs,uid);EssayWorker(app.state.store,fake,lambda:clock[0]).run_once()
    groups=jobs.evolution(uid)['groups']
    assert len(groups)==2 and all(len(g['items'])==1 for g in groups)


@pytest.mark.parametrize('code,retryable',[(401,False),(429,True),(500,True)])
def test_provider_status_controls_retry_without_exposing_body(code,retryable):
    evaluator=OpenAIEvaluator('synthetic-key','synthetic-model',httpx.MockTransport(lambda r:httpx.Response(code,json={'secret':'must-not-surface'})))
    with pytest.raises(ProviderFailure) as exc:evaluator.evaluate('Tema',TEXT)
    assert exc.value.retryable is retryable and exc.value.code=='provider_unavailable'


def test_real_feature_requires_both_activation_flags(tmp_path,monkeypatch):
    from backend.moirae.app import create_app
    monkeypatch.setenv('MOIRAE_ESSAY_AI','true');monkeypatch.setenv('MOIRAE_ESSAY_AI_REVIEWED','false');monkeypatch.setenv('MOIRAE_ESSAY_MODEL','synthetic-model')
    app=create_app(str(tmp_path/'db'),origin=BASE,secure=False)
    c,uid=register(app,'gated@example.test');grant(app,uid)
    assert c.get('/api/essay-evaluations').status_code==503
