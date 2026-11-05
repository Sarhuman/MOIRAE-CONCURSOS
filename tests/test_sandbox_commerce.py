from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.moirae.store import Store
from backend.moirae.sandbox_wallet import SandboxWallet
from backend.moirae.sandbox_coupons import SandboxCoupons
from backend.moirae.app import create_app


@pytest.fixture
def env(tmp_path):
    store=Store(str(tmp_path/'sandbox.sqlite3'))
    with store.connect(write=True) as db:
        for uid in ('u','v'):
            db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,uid+'@example.test','unused',1))
    now=[1000]
    return store,SandboxWallet(store,True,lambda:now[0]),SandboxCoupons(store,True,lambda:now[0]),now


def campaign(c,max_uses=10,products=None):
    c.configure('test',900,3000,500,products or ['essencial'],[dict(discount_bps=1000,weight=1)],max_uses)


def fails(code,call):
    with pytest.raises(HTTPException) as exc:call()
    assert exc.value.status_code==code


def test_wallet_fefo_retry_expiry_and_release(env):
    store,w,_,now=env
    late=w.grant('u','late',2,2500)
    soon=w.grant('u','soon',1,1100)
    assert w.grant('u','soon',1,1100)==soon
    fails(409,lambda:w.grant('v','soon',1,1100))
    r=w.reserve('u','job-1')
    assert r['lot_id']==soon
    assert w.reserve('u','job-1')==r
    assert w.snapshot('u')['available']==2
    fails(404,lambda:w.settle('v',r['id'],'consume'))
    now[0]=1100
    fails(409,lambda:w.settle('u',r['id'],'consume'))
    assert w.settle('u',r['id'],'release')['status']=='released'
    assert w.settle('u',r['id'],'release')['status']=='released'
    assert w.snapshot('u')['available']==2
    assert w.reserve('u','job-2')['lot_id']==late
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM sandbox_wallet_events WHERE kind='release'").fetchone()[0]==1


def test_wallet_consumption_refund_revocation_and_invariants(env):
    store,w,_,_=env
    lid=w.grant('u','grant',2,2000)
    r=w.reserve('u','a')
    assert w.settle('u',r['id'],'consume')['status']=='consumed'
    w.settle('u',r['id'],'consume')
    fails(409,lambda:w.settle('u',r['id'],'release'))
    w.settle('u',r['id'],'refund');w.settle('u',r['id'],'refund')
    assert w.snapshot('u')['available']==2
    pending=w.reserve('u','b')
    w.revoke('u',lid);w.revoke('u',lid)
    assert w.snapshot('u')['available']==0
    assert w.settle('u',pending['id'],'release')['status']=='released'
    fails(409,lambda:w.settle('u',pending['id'],'consume'))
    with store.connect() as db:
        assert all(r['available']+r['reserved']+r['consumed']==r['units'] for r in db.execute('SELECT * FROM sandbox_credit_lots'))
        assert db.execute("SELECT count(*) FROM sandbox_wallet_events WHERE kind='refund'").fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM essay_credit_events').fetchone()[0]==0


def test_wallet_concurrent_reservation_and_terminal_race(env):
    _,w,_,_=env
    w.grant('u','only',1,2000)
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(lambda _:w.reserve('u','same'),range(5)))
    assert len({r['id'] for r in rows})==1
    fails(409,lambda:w.reserve('u','another'))
    def settle(action):
        try:return w.settle('u',rows[0]['id'],action)['status']
        except HTTPException as exc:return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(settle,['consume','release']))
    assert results.count(409)==1
    assert w.snapshot('u')['available'] in (0,1)


def test_coupon_same_draw_quote_and_immutable_configuration(env):
    _,_,c,_=env;campaign(c)
    campaign(c)
    fails(409,lambda:c.configure('test',900,3000,500,['avancado'],[dict(discount_bps=1000,weight=1)],10))
    with ThreadPoolExecutor(max_workers=5) as pool:
        draws=list(pool.map(lambda _:c.draw('u','test'),range(5)))
    assert all(d==draws[0] for d in draws)
    code=draws[0]['code']
    rules=c.rules('test')
    assert rules['outcomes']==[dict(discount_bps=1000,weight=1,total_weight=1)]
    q=c.quote('u',code,'essencial')
    assert (q['amount_cents'],q['discount_cents'],q['total_cents'])==(4400,440,3960)
    assert q['checkout_available'] is False
    fails(409,lambda:c.quote('v',code,'essencial'))
    fails(409,lambda:c.quote('u',code,'avancado'))


def test_coupon_redemption_idempotency_cap_expiry_and_snapshots(env):
    _,_,c,now=env;campaign(c,max_uses=1)
    a=c.draw('u','test')['code'];b=c.draw('v','test')['code']
    q=c.redeem('u',a,'essencial','test-order')
    assert c.redeem('u',a,'essencial','test-order')==q
    fails(409,lambda:c.redeem('v',b,'essencial','test-order'))
    fails(409,lambda:c.redeem('u',a,'essencial','new-order'))
    fails(409,lambda:c.redeem('v',b,'essencial','other-order'))
    now[0]=1500
    fails(409,lambda:c.quote('v',b,'essencial'))
    assert c.draw('v','test')['code']==b # no reroll after expiry
    assert c.redeem('u',a,'essencial','test-order')==q # preserved receipt


def test_coupon_global_cap_is_atomic(env):
    _,_,c,_=env;campaign(c,max_uses=1)
    codes={u:c.draw(u,'test')['code'] for u in ('u','v')}
    def redeem(u):
        try:c.redeem(u,codes[u],'essencial','order-'+u);return 200
        except HTTPException as exc:return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(redeem,['u','v']))==[200,409]


def test_services_disabled_and_http_has_no_topup_or_redemption(env):
    store,_,_,_=env
    fails(503,lambda:SandboxWallet(store).snapshot('u'))
    fails(503,lambda:SandboxCoupons(store).draw('u','test'))
    app=create_app(store.path,origin='http://localhost:8000',secure=False)
    c=TestClient(app,base_url='http://localhost:8000')
    assert c.get('/api/sandbox/wallet').status_code==401
    paths={route.path for route in app.routes}
    assert '/api/sandbox/wallet/grant' not in paths
    assert '/api/sandbox/coupons/redeem' not in paths


def test_sandbox_endpoints_auth_csrf_and_account_export(tmp_path,monkeypatch):
    monkeypatch.setenv('MOIRAE_COMMERCE_SANDBOX','true')
    app=create_app(str(tmp_path/'api.sqlite3'),origin='http://localhost:8000',secure=False)
    c=TestClient(app,base_url='http://localhost:8000',headers={'Origin':'http://localhost:8000'})
    password='senha-exclusiva-123'
    r=c.post('/api/auth/register',json=dict(email='sandbox@example.test',password=password,accept_terms=True,adult_pilot=True))
    c.headers['X-CSRF-Token']=r.json()['csrf']
    token=app.state.mailer.messages[-1]['link'].split('#token=')[1]
    assert c.post('/api/auth/verify-email',json={'token':token}).status_code==200
    assert c.get('/api/sandbox/wallet').json()['available']==0
    campaign(app.state.coupons) # fake fixed clock for domain fixture only; API gets explicit clock below
    app.state.coupons.clock=lambda:1000
    with app.state.store.connect() as db:
        uid=db.execute('SELECT id FROM users WHERE email=?',('sandbox@example.test',)).fetchone()[0]
    app.state.wallet.grant(uid,'local-only',2,9999999999)
    assert c.post('/api/sandbox/coupons/draw',json={'campaign':'test','accepted_rules':True},headers={'X-CSRF-Token':'bad'}).status_code==403
    assert c.post('/api/sandbox/coupons/draw',json={'campaign':'test','accepted_rules':True},headers={'Origin':'https://other.test'}).status_code==403
    draw=c.post('/api/sandbox/coupons/draw',json={'campaign':'test','accepted_rules':True})
    assert draw.status_code==200
    assert c.post('/api/sandbox/coupons/quote',json={'code':draw.json()['code'],'product':'essencial','total_cents':1}).status_code==422
    exported=c.post('/api/account/export',json={'password':password}).json()
    assert len(exported['sandbox_wallet']['lots'])==1
    assert len(exported['sandbox_coupons'])==1
    assert c.post('/api/account/delete',json={'password':password,'confirmation':'EXCLUIR'}).status_code==200
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM sandbox_credit_lots').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM sandbox_coupons').fetchone()[0]==0


def test_refund_after_expiry_does_not_restore_spendable_balance(env):
    _,w,_,now=env
    w.grant('u','expiring',1,1100)
    r=w.reserve('u','essay')
    w.settle('u',r['id'],'consume')
    now[0]=1100
    w.settle('u',r['id'],'refund')
    assert w.snapshot('u')['available']==0
    fails(409,lambda:w.reserve('u','new-essay'))

def test_coupon_disabled_campaign_and_invalid_probability(env):
    store,_,c,_=env;campaign(c)
    code=c.draw('u','test')['code']
    with store.connect(write=True) as db:
        db.execute("UPDATE sandbox_coupon_campaigns SET enabled=0 WHERE id='test'")
    fails(404,lambda:c.quote('u',code,'essencial'))
    fails(404,lambda:c.draw('u','test'))
    with pytest.raises(ValueError):
        c.configure('bad',900,3000,500,['essencial'],[dict(discount_bps=1000,weight=0)],10)

def test_restart_preserves_reservations_and_receipts(env):
    store,w,c,_=env;campaign(c)
    w.grant('u','persistent',2,2000)
    r=w.reserve('u','job')
    code=c.draw('u','test')['code']
    receipt=c.redeem('u',code,'essencial','order')
    fresh=Store(store.path)
    assert SandboxWallet(fresh,True,lambda:1000).reserve('u','job')==r
    assert SandboxCoupons(fresh,True,lambda:1000).redeem('u',code,'essencial','order')==receipt


def test_account_deletion_cannot_replenish_global_coupon_cap(env):
    store,_,c,_=env;campaign(c,max_uses=1)
    a=c.draw('u','test')['code']
    b=c.draw('v','test')['code']
    c.redeem('u',a,'essencial','order-deleted-account')
    with store.connect(write=True) as db:
        db.execute("DELETE FROM users WHERE id='u'")
    fails(409,lambda:c.redeem('v',b,'essencial','other'))
    assert c.rules('test')['max_uses']==1
    with store.connect() as db:
        assert db.execute('SELECT used_count FROM sandbox_coupon_campaigns').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM sandbox_coupon_redemptions').fetchone()[0]==0

def test_v11_coupon_migration_preserves_usage_and_is_repeatable(tmp_path):
    path=tmp_path/'old.sqlite3'
    store=Store(str(path))
    with store.connect(write=True) as db:
        db.execute("INSERT INTO users VALUES('u','u@example.test','unused',1)")
    c=SandboxCoupons(store,True,lambda:1000);campaign(c,max_uses=1)
    code=c.draw('u','test')['code']
    receipt=c.redeem('u',code,'essencial','migrated-order')
    with store.connect(write=True) as db:
        db.execute('ALTER TABLE sandbox_coupon_campaigns DROP COLUMN used_count')
        db.execute('DELETE FROM schema_version WHERE version=12')
    fresh=Store(str(path));Store(str(path))
    with fresh.connect() as db:
        assert db.execute('SELECT used_count FROM sandbox_coupon_campaigns').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM schema_version WHERE version=12').fetchone()[0]==1
    assert SandboxCoupons(fresh,True,lambda:1000).redeem('u',code,'essencial','migrated-order')==receipt
