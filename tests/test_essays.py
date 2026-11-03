import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.moirae.app import create_app
from backend.moirae.essays import DemoEvaluator, Evaluation, validate_result
from backend.moirae.store import Store

BASE='http://localhost:8000'
PASSWORD='senha-exclusiva-123'
TEXT='🌱 Educação e participação social. ' * 12

def register(app,c,email):
    response=c.post('/api/auth/register',json=dict(email=email,password=PASSWORD,accept_terms=True,adult_pilot=True))
    assert response.status_code==201
    c.headers['X-CSRF-Token']=response.json()['csrf']
    assert c.post('/api/auth/verify-email',json={'token':app.state.mailer.messages[-1]['link'].split('#token=')[1]}).status_code==200
    with app.state.store.connect() as db:return db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()[0]

@pytest.fixture
def setup(tmp_path):
    app=create_app(str(tmp_path/'db'),origin=BASE,secure=False,essay_demo=True)
    c=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    uid=register(app,c,'essay@example.test');now=int(time.time())
    with app.state.store.connect(write=True) as db:
        db.execute("INSERT INTO billing_orders(id,user_id,plan_id,amount_cents,status,created_at,request_key) VALUES('order',?,'essencial',3500,'approved',?,'checkout')",(uid,now))
        db.execute("INSERT INTO access_grants VALUES('order',?,'essencial',?,?,'active',3)",(uid,now-1,now+86400))
    return app,c,uid

def submit(c,key=None,text=TEXT):
    return c.post('/api/essays',json=dict(key=key or str(uuid.uuid4()),theme='Educação e sociedade',text=text))

def test_complete_workflow_persists_and_exports(setup):
    app,c,uid=setup;key=str(uuid.uuid4());r=submit(c,key);assert r.status_code==201
    eid=r.json()['id'];assert submit(c,key).json()==r.json()
    assert c.get('/api/essays').json()['remaining']==2
    assert c.post(f'/api/essays/{eid}/process',json={}).json()['status']=='completed'
    assert c.post(f'/api/essays/{eid}/process',json={}).json()['status']=='completed'
    d=c.get('/api/essays/'+eid).json();assert d['text']==TEXT and len(d['result']['competencies'])==5
    body=dict(key=str(uuid.uuid4()),annotation_id='demo-opening',text='Uma nova versão da ideia inicial com mais clareza.')
    rewrite=c.post(f'/api/essays/{eid}/rewrites',json=body);assert rewrite.status_code==201
    assert c.post(f'/api/essays/{eid}/rewrites',json=body).json()==rewrite.json()
    assert len(c.get('/api/essays/'+eid).json()['rewrites'])==1
    assert c.get('/api/essays').json()['remaining']==2
    restarted=create_app(app.state.store.path,origin=BASE,secure=False,essay_demo=True)
    assert restarted.state.essays.detail(uid,eid)['rewrites'][0]['text']==body['text']
    export=c.post('/api/account/export',json={'password':PASSWORD}).json()
    assert export['essays'][0]['text']==TEXT and len(export['essays'][0]['rewrites'])==1
    assert 'password_hash' not in json.dumps(export)
    with app.state.store.connect() as db:assert db.execute('SELECT essay_credits FROM access_grants').fetchone()[0]==3

def test_permissions_csrf_and_disabled(tmp_path,setup):
    app,c,uid=setup;eid=submit(c).json()['id']
    stranger=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    assert stranger.get('/api/essays').status_code==401
    register(app,stranger,'other@example.test')
    assert stranger.get('/api/essays/'+eid).status_code==404
    assert stranger.post(f'/api/essays/{eid}/process',json={}).status_code==404
    assert submit(stranger).status_code==403
    assert c.post('/api/essays',json=dict(key=str(uuid.uuid4()),theme='Tema',text=TEXT),headers={'X-CSRF-Token':'bad'}).status_code==403
    app.state.essays.enabled=False
    assert c.get('/api/essays').status_code==503
    disabled=create_app(str(tmp_path/'disabled'),origin=BASE,secure=False)
    assert disabled.state.essays.enabled is False

def test_concurrent_quota_and_retries(setup):
    app,c,uid=setup;svc=app.state.essays
    def attempt(_):
        try:return svc.submit(uid,str(uuid.uuid4()),'Tema',TEXT)['status']
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(8)))
    assert results.count('received')==3 and results.count(409)==5
    assert svc.history(uid)['remaining']==0

def test_concurrent_same_key_single_reservation(setup):
    app,c,uid=setup;key=str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(lambda _:app.state.essays.submit(uid,key,'Tema',TEXT),range(6)))
    assert len({r['id'] for r in results})==1
    assert app.state.essays.history(uid)['remaining']==2
    assert submit(c,key,TEXT+'alterado').status_code==409

@pytest.mark.parametrize('kind',['failure','invalid'])
def test_failure_releases_credit_without_retrying_provider(setup,kind):
    app,c,uid=setup
    class Broken:
        calls=0
        def evaluate(self,theme,text):
            self.calls+=1
            if kind=='failure':raise TimeoutError('private content must never escape')
            value=DemoEvaluator().evaluate(theme,text);value['annotations'][0]['quote']='wrong';return value
    broken=Broken();app.state.essays.evaluator=broken
    eid=submit(c).json()['id']
    assert c.post(f'/api/essays/{eid}/process',json={}).json()['status']=='failed'
    assert c.post(f'/api/essays/{eid}/process',json={}).json()['status']=='failed'
    assert broken.calls==1 and c.get('/api/essays').json()['remaining']==3
    assert 'private content' not in c.get('/api/essays/'+eid).text

def test_expired_grant_releases_reservation_but_keeps_history(setup):
    app,c,uid=setup;eid=submit(c).json()['id'];app.state.essays.clock=lambda:time.time()+172800
    assert app.state.essays.process(uid,eid)['status']=='failed'
    assert app.state.essays.detail(uid,eid)['text']==TEXT
    with pytest.raises(HTTPException):app.state.essays.submit(uid,str(uuid.uuid4()),'Tema',TEXT)

@pytest.mark.parametrize('mutation',['offset','duplicate','score','extra','surrogate'])
def test_schema_and_utf16_validation(mutation):
    value=DemoEvaluator().evaluate('Tema',TEXT);assert validate_result(value,TEXT)
    if mutation=='offset':value['annotations'][0]['end']=100000
    if mutation=='duplicate':value['competencies'][1]['id']=1
    if mutation=='score':value['competencies'][0]['score']=199
    if mutation=='extra':value['unexpected']='x'
    if mutation=='surrogate':value['annotations'][0]['start']=1
    with pytest.raises(ValueError):validate_result(value,TEXT)

def test_rewrite_limits_and_original_immutable(setup):
    app,c,uid=setup;eid=submit(c).json()['id'];svc=app.state.essays
    with pytest.raises(HTTPException):svc.rewrite(uid,eid,str(uuid.uuid4()),'demo-opening','Texto de teste')
    svc.process(uid,eid)
    with pytest.raises(HTTPException):svc.rewrite(uid,eid,str(uuid.uuid4()),'invented','Texto de teste')
    for i in range(10):svc.rewrite(uid,eid,str(uuid.uuid4()),'demo-opening',f'Uma reescrita demonstrativa número {i}.')
    with pytest.raises(HTTPException):svc.rewrite(uid,eid,str(uuid.uuid4()),'demo-opening','Outra versão')
    assert svc.detail(uid,eid)['text']==TEXT

def test_empty_and_unpaired_unicode_rejected(setup):
    app,c,uid=setup
    assert submit(c,text=' '*100).status_code==422
    payload=dict(key=str(uuid.uuid4()),theme='Tema',text='a'*100+'\ud800')
    assert c.post('/api/essays',content=json.dumps(payload),headers={'Content-Type':'application/json'}).status_code==422

def test_additive_schema_reopen(setup):
    app,c,uid=setup;eid=submit(c).json()['id']
    Store(app.state.store.path)
    assert app.state.essays.detail(uid,eid)['text']==TEXT

def test_committed_schema_and_fixture():
    from pathlib import Path
    assert json.loads(Path('data/essay-demo-schema.json').read_text())==Evaluation.model_json_schema()
    fixture=json.loads(Path('data/essay-demo-fixture.json').read_text())
    assert validate_result(fixture['result'],fixture['text'])
