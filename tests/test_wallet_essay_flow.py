import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.moirae.local_playtest import create_playtest
from backend.moirae.app import create_app
from backend.moirae.store import Store

BASE='http://localhost:8000'
TEXT='Educação e participação social devem caminhar juntas para ampliar o acesso aos estudos. '*3

@pytest.fixture
def env(tmp_path,monkeypatch):
    monkeypatch.setenv('MOIRAE_COMMERCE_SANDBOX','true')
    path=tmp_path/'flow.sqlite3'
    create_playtest(path,'flow@example.test','senha-exclusiva-123',wallet_credits=2)
    app=create_app(str(path),origin=BASE,secure=False,essay_demo=True)
    c=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    r=c.post('/api/auth/login',json={'email':'flow@example.test','password':'senha-exclusiva-123'})
    assert r.status_code==200
    c.headers['X-CSRF-Token']=r.json()['csrf']
    return app,c

def payload(key=None):
    return dict(key=key or str(uuid.uuid4()),theme='Acesso à educação',text=TEXT,funding='sandbox_wallet')

def send(c,body=None):return c.post('/api/essays',json=body or payload())
def balance(c):return c.get('/api/sandbox/wallet').json()
def process(c,eid):return c.post('/api/essays/'+eid+'/process',json={})

def test_wallet_complete_flow_and_idempotent_requests(env):
    app,c=env;body=payload()
    before=c.get('/api/essays').json()['remaining']
    r=send(c,body);assert r.status_code==201,r.text
    eid=r.json()['id']
    assert send(c,body).json()==r.json()
    assert balance(c)['available']==1
    assert balance(c)['lots'][0]['reserved']==1
    assert c.get('/api/essays').json()['remaining']==before
    assert c.get('/api/essays/'+eid).json()['funding']=='sandbox_wallet'
    assert process(c,eid).json()['status']=='completed'
    assert process(c,eid).json()['status']=='completed'
    assert balance(c)['lots'][0]['consumed']==1
    assert balance(c)['lots'][0]['reserved']==0
    assert c.get('/api/essays').json()['remaining']==before
    assert send(c,{**body,'funding':'plan_demo'}).status_code==409
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM essay_credit_events').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM real_essay_jobs').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM sandbox_essay_credits').fetchone()[0]==1


def test_evaluation_failure_releases_wallet_once(env):
    app,c=env
    class Broken:
        def evaluate(self,*args):raise RuntimeError('synthetic failure')
    app.state.essays.evaluator=Broken()
    eid=send(c).json()['id']
    assert process(c,eid).json()['status']=='failed'
    assert process(c,eid).json()['status']=='failed'
    assert balance(c)['available']==2
    assert balance(c)['lots'][0]['reserved']==0
    assert len([e for e in balance(c)['events'] if e['kind']=='release'])==1


def test_empty_wallet_rolls_back_essay_creation(env):
    app,c=env
    assert send(c).status_code==201
    assert send(c).status_code==201
    assert send(c).status_code==409
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM essay_submissions').fetchone()[0]==2
        assert db.execute('SELECT count(*) FROM sandbox_credit_reservations').fetchone()[0]==2


def test_concurrent_submission_and_process_use_one_credit(env):
    app,c=env;body=payload();cookies=dict(c.cookies);headers=dict(c.headers)
    def call(_):
        with TestClient(app,base_url=BASE,cookies=cookies,headers=headers) as client:return send(client,body)
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(call,range(4)))
    assert all(r.status_code==201 for r in rows)
    assert len({r.json()['id'] for r in rows})==1
    eid=rows[0].json()['id']
    def finish(_):
        with TestClient(app,base_url=BASE,cookies=cookies,headers=headers) as client:return process(client,eid)
    with ThreadPoolExecutor(max_workers=4) as pool:done=list(pool.map(finish,range(4)))
    assert all(r.json()['status']=='completed' for r in done)
    assert balance(c)['lots'][0]['consumed']==1


def test_revoked_or_expired_credit_cannot_complete(env):
    app,c=env
    eid=send(c).json()['id']
    with app.state.store.connect() as db:
        lot=db.execute('SELECT id,user_id FROM sandbox_credit_lots').fetchone()
    app.state.wallet.revoke(lot['user_id'],lot['id'])
    assert process(c,eid).json()['status']=='failed'
    assert balance(c)['available']==0
    assert balance(c)['lots'][0]['consumed']==0


def test_restart_persists_link_and_disabled_wallet_preserves_reservation(env):
    app,c=env;eid=send(c).json()['id']
    app.state.wallet.enabled=False
    assert process(c,eid).status_code==503
    app.state.wallet.enabled=True
    assert balance(c)['lots'][0]['reserved']==1
    fresh=create_app(app.state.store.path,origin=BASE,secure=False,essay_demo=True)
    client=TestClient(fresh,base_url=BASE,cookies=dict(c.cookies),headers=dict(c.headers))
    assert process(client,eid).json()['status']=='completed'
    assert balance(client)['lots'][0]['consumed']==1


def test_real_submission_rejects_sandbox_funding(env):
    app,c=env
    assert c.post('/api/essay-evaluations',json={**payload(),'accept_external':True}).status_code==422
    body=payload();body.pop('funding')
    assert c.post('/api/essay-evaluations',json={**body,'accept_external':True}).status_code==503
    assert balance(c)['available']==2
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM real_essay_jobs').fetchone()[0]==0


def test_coupon_configuration_default_and_server_draw(env,monkeypatch):
    app,c=env
    assert c.get('/api/coupon-experience').json()['mode']=='demonstration'
    now=int(app.state.coupons.clock())
    app.state.coupons.configure('configured-test',now-1,now+3600,600,['essencial'],[dict(discount_bps=1000,weight=1)],5)
    monkeypatch.setenv('MOIRAE_COUPON_CAMPAIGN','configured-test')
    experience=c.get('/api/coupon-experience').json()
    assert experience['mode']=='sandbox'
    assert experience['rules']['id']=='configured-test'
    assert c.post('/api/sandbox/coupons/draw',json={'campaign':'configured-test'}).status_code==422
    body={'campaign':'configured-test','accepted_rules':True}
    first=c.post('/api/sandbox/coupons/draw',json=body)
    assert first.status_code==200
    assert c.post('/api/sandbox/coupons/draw',json=body).json()==first.json()
    assert c.get('/carteira').status_code==200


def test_link_failure_rolls_back_credit_and_submission(env):
    import sqlite3
    app,c=env
    with app.state.store.connect(write=True) as db:
        db.execute("CREATE TRIGGER fail_link BEFORE INSERT ON sandbox_essay_credits BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    with pytest.raises(sqlite3.IntegrityError):send(c)
    assert balance(c)['available']==2
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM essay_submissions').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM sandbox_credit_reservations').fetchone()[0]==0

def test_expired_access_releases_reservation(env):
    app,c=env
    eid=send(c).json()['id']
    with app.state.store.connect(write=True) as db:
        db.execute('UPDATE access_grants SET ends_at=0')
    assert process(c,eid).json()['status']=='failed'
    assert balance(c)['available']==2

def test_wallet_expiry_does_not_restore_available_balance(env):
    app,c=env
    eid=send(c).json()['id']
    with app.state.store.connect(write=True) as db:
        db.execute('UPDATE sandbox_credit_lots SET expires_at=0')
    assert process(c,eid).json()['status']=='failed'
    assert balance(c)['available']==0
    assert balance(c)['lots'][0]['reserved']==0

def test_wallet_essay_and_reservation_are_isolated_between_accounts(env):
    app,owner=env
    eid=send(owner).json()['id']
    other=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    created=other.post('/api/auth/register',json={'email':'isolated@example.test','password':'synthetic-isolation-password','accept_terms':True,'adult_pilot':True})
    assert created.status_code==201
    other.headers['X-CSRF-Token']=created.json()['csrf']
    token=app.state.mailer.messages[-1]['link'].split('#token=')[1]
    assert other.post('/api/auth/verify-email',json={'token':token}).status_code==200
    assert other.get('/api/essays/'+eid).status_code==404
    assert process(other,eid).status_code==404
    assert balance(other)['available']==0 and balance(other)['lots']==[]
    assert balance(owner)['lots'][0]['reserved']==1
    assert balance(owner)['lots'][0]['consumed']==0
    assert process(owner,eid).json()['status']=='completed'
    assert balance(owner)['lots'][0]['consumed']==1


def test_approved_coupon_policy_over_authenticated_api(env,monkeypatch):
    # Dates and cap here are isolated test fixtures, never an operational campaign.
    from test_approved_coupon_policy import stamp
    app,winner=env
    now=[stamp(2026,11,4)]
    app.state.coupons.clock=lambda:now[0]
    app.state.coupons.configure_approved('approved-api-fixture',now[0]-1,now[0]+60,10)
    monkeypatch.setenv('MOIRAE_COUPON_CAMPAIGN','approved-api-fixture')
    loser=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    created=loser.post('/api/auth/register',json={'email':'loser@example.test','password':'synthetic-loser-password','accept_terms':True,'adult_pilot':True})
    assert created.status_code==201
    loser.headers['X-CSRF-Token']=created.json()['csrf']
    token=app.state.mailer.messages[-1]['link'].split('#token=')[1]
    assert loser.post('/api/auth/verify-email',json={'token':token}).status_code==200
    tickets=iter([0,1])
    monkeypatch.setattr('backend.moirae.sandbox_coupons.secrets.randbelow',lambda limit:next(tickets))
    rules=winner.get('/api/coupon-experience').json()['rules']
    assert rules['valid_months']==3 and rules['products']==['avancado']
    body={'campaign':'approved-api-fixture','accepted_rules':True}
    won=winner.post('/api/sandbox/coupons/draw',json=body).json()
    lost=loser.post('/api/sandbox/coupons/draw',json=body).json()
    assert won['won'] and won['discount_bps']==500
    assert not lost['won'] and lost['code'] is None
    assert winner.post('/api/sandbox/coupons/draw',json=body).json()==won
    assert loser.post('/api/sandbox/coupons/draw',json=body).json()==lost
    quote={'code':won['code'],'product':'avancado'}
    assert loser.post('/api/sandbox/coupons/quote',json=quote).status_code==409
    assert winner.post('/api/sandbox/coupons/quote',json={**quote,'product':'essencial'}).status_code==409
    now[0]+=3600
    r=winner.post('/api/sandbox/coupons/quote',json=quote)
    assert r.status_code==200 and r.json()['total_cents']==10450
    now[0]=won['expires_at']
    assert winner.post('/api/sandbox/coupons/quote',json=quote).status_code==409
