"""Financial lifecycle with synthetic provider responses; no external payment calls."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.moirae.app import create_app
from backend.moirae.store import Store
from backend.moirae.plans import PLANS
from test_billing import FakeProvider, register, BASE, SECRET, PASSWORD, notify


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv('MOIRAE_COMMERCE_SANDBOX','true')
    fake=FakeProvider()
    app=create_app(str(tmp_path/'db'),origin=BASE,secure=False,billing_provider=fake,billing_collector='123',billing_secret=SECRET,sandbox_pack_validity_days=90)
    clock=[1793800000]
    for service in (app.state.billing,app.state.wallet,app.state.coupons):service.clock=lambda:clock[0]
    with app.state.store.connect(write=True) as db:
        for uid in ('alice','bob'):
            db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,uid+'@example.test','synthetic-not-a-password',clock[0]))
    return app,fake,clock


def start(env, uid='alice', product='creditos-5', key=None, code=None):
    return env[0].state.billing.start(uid,product,key or str(uuid.uuid4()),coupon_code=code,kind='credit_pack' if product.startswith('creditos-') else 'plan')


def pay(env, oid, status='approved', amount=27.5, pid='100', **updates):
    app,fake,clock=env
    fake.payments[pid]=dict(id=int(pid),external_reference=oid,currency_id='BRL',collector_id=123,transaction_amount=amount,transaction_amount_refunded=0,live_mode=False,status=status,date_last_updated=datetime.fromtimestamp(clock[0],timezone.utc).isoformat(),**updates)
    return app.state.billing.reconcile(pid)


def contract(env, oid):
    with env[0].state.store.connect() as db:return dict(db.execute('SELECT * FROM sandbox_order_contracts WHERE order_id=?',(oid,)).fetchone())


def winner(env, uid='alice', campaign='approved', cap=10):
    app,_,clock=env
    app.state.coupons.configure_approved(campaign,clock[0]-1,clock[0]+1000,cap)
    # Patch only the server's random ticket, preserving the versioned 1/100 policy.
    from unittest.mock import patch
    with patch('backend.moirae.sandbox_coupons.secrets.randbelow',return_value=0):
        return app.state.coupons.draw(uid,campaign)['code']


@pytest.mark.parametrize('product,total,credits',[('creditos-5',2750,5),('creditos-10',4950,10),('creditos-30',13200,30)])
def test_paid_pack_snapshot_and_duplicate_notifications(env,product,total,credits):
    app,_,clock=env;key=str(uuid.uuid4());order=start(env,product=product,key=key);oid=order['order_id']
    assert app.state.wallet.snapshot('alice')['available']==0
    assert start(env,product=product,key=key)==order
    assert pay(env,oid,'pending',total/100)=={'ok':True}
    assert app.state.wallet.snapshot('alice')['available']==0
    clock[0]+=1;assert pay(env,oid,amount=total/100)=={'ok':True}
    before=app.state.wallet.snapshot('alice')
    clock[0]+=60;assert pay(env,oid,amount=total/100)=={'ok':True}
    assert app.state.wallet.snapshot('alice')==before
    assert before['available']==credits and len(before['lots'])==1
    assert before['lots'][0]['expires_at']==clock[0]-60+90*86400
    assert contract(env,oid)['state']=='fulfilled'
    with app.state.store.connect() as db:
        assert db.execute('SELECT amount_cents FROM billing_orders').fetchone()[0]==total
        assert db.execute('SELECT count(*) FROM access_grants').fetchone()[0]==0
    assert app.state.wallet.snapshot('bob')['available']==0


def test_concurrent_reconciliation_and_restart_preserve_lot(env):
    app,fake,clock=env;oid=start(env)['order_id'];pay(env,oid)
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(r=={'ok':True} for r in pool.map(lambda _:app.state.billing.reconcile('100'),range(8)))
    before=app.state.wallet.snapshot('alice');row=contract(env,oid)
    Store(app.state.store.path);Store(app.state.store.path)
    assert app.state.wallet.snapshot('alice')==before and contract(env,oid)==row
    assert len(before['events'])==1


@pytest.mark.parametrize('field,value',[('transaction_amount',1),('currency_id','USD'),('collector_id',999),('live_mode',True)])
def test_invalid_server_payment_never_grants(env,field,value):
    app,fake,_=env;oid=start(env)['order_id'];pay(env,oid,'pending');fake.payments['100'][field]=value;fake.payments['100']['status']='approved'
    with pytest.raises(HTTPException) as e:app.state.billing.reconcile('100')
    assert e.value.status_code==400 and app.state.wallet.snapshot('alice')['available']==0


def test_fulfillment_rolls_back_payment_and_wallet_together(env,monkeypatch):
    app,fake,_=env;oid=start(env)['order_id'];pay(env,oid,'pending')
    original=app.state.wallet.event
    def fail(*args):
        original(*args)
        raise RuntimeError('synthetic disk failure')
    monkeypatch.setattr(app.state.wallet,'event',fail);fake.payments['100']['status']='approved'
    with pytest.raises(RuntimeError):app.state.billing.reconcile('100')
    assert app.state.wallet.snapshot('alice')['available']==0
    assert contract(env,oid)['state']=='pending'
    monkeypatch.setattr(app.state.wallet,'event',original)
    assert app.state.billing.reconcile('100')=={'ok':True}
    assert app.state.wallet.snapshot('alice')['available']==5


@pytest.mark.parametrize('status',['rejected','cancelled','refunded','charged_back'])
def test_revocation_releases_reservations_without_erasing_consumption(env,status):
    app,_,clock=env;oid=start(env)['order_id'];pay(env,oid)
    consumed=app.state.wallet.reserve('alice','used');app.state.wallet.settle('alice',consumed['id'],'consume')
    reserved=app.state.wallet.reserve('alice','pending');clock[0]+=1
    assert pay(env,oid,status)['review_required'] is True
    balance=app.state.wallet.snapshot('alice');assert balance['available']==0
    assert balance['lots'][0]['consumed']==1 and balance['lots'][0]['reserved']==0
    assert balance['lots'][0]['status']=='revoked'
    with app.state.store.connect() as db:
        assert db.execute('SELECT status FROM sandbox_credit_reservations WHERE id=?',(reserved['id'],)).fetchone()[0]=='released'
    clock[0]+=1;assert pay(env,oid)['review_required'] is True
    assert app.state.wallet.snapshot('alice')['available']==0


def test_full_unused_refund_and_stale_events_cannot_restore_lot(env):
    app,fake,clock=env;oid=start(env)['order_id'];pay(env,oid);approved=fake.payments['100'].copy()
    clock[0]+=1;assert pay(env,oid,'refunded')=={'ok':True}
    fake.payments['100']=approved;assert app.state.billing.reconcile('100')['ignored']=='older_version'
    clock[0]+=1;assert pay(env,oid)['ignored']=='terminal_state'
    assert app.state.wallet.snapshot('alice')['available']==0


def test_partial_refund_requires_manual_monetary_decision(env):
    app,fake,clock=env;oid=start(env)['order_id'];pay(env,oid);clock[0]+=1
    fake.payments['100']['transaction_amount_refunded']=1
    fake.payments['100']['date_last_updated']=datetime.fromtimestamp(clock[0],timezone.utc).isoformat()
    assert app.state.billing.reconcile('100')['review_required'] is True
    assert app.state.wallet.snapshot('alice')['available']==0
    assert contract(env,oid)['review_reason']


def test_lot_expiry_and_late_payment_are_separate(env):
    app,_,clock=env;oid=start(env)['order_id'];clock[0]+=1800
    assert pay(env,oid)['review_required'] is True
    assert app.state.wallet.snapshot('alice')['available']==0
    oid2=start(env)['order_id'];pay(env,oid2,pid='101');clock[0]+=90*86400
    assert app.state.wallet.snapshot('alice')['available']==0
    with pytest.raises(HTTPException):app.state.wallet.reserve('alice','expired')


def test_cancel_is_owner_only_and_late_payment_requires_review(env):
    app,_,_=env;oid=start(env)['order_id']
    with pytest.raises(HTTPException) as e:app.state.billing.cancel_sandbox('bob',oid)
    assert e.value.status_code==404
    assert app.state.billing.cancel_sandbox('alice',oid)['cancelled'] is True
    assert app.state.billing.cancel_sandbox('alice',oid)['cancelled'] is True
    assert pay(env,oid)['review_required'] is True
    assert app.state.wallet.snapshot('alice')['available']==0


def test_coupon_hold_snapshot_idempotency_and_paid_use(env,monkeypatch):
    app,_,_=env;code=winner(env);key=str(uuid.uuid4());order=start(env,product='avancado',code=code,key=key)
    assert start(env,product='avancado',code=code,key=key)==order
    with pytest.raises(HTTPException):app.state.coupons.quote('alice',code,'avancado')
    snapshot=json.loads(contract(env,order['order_id'])['snapshot'])
    assert (snapshot['amount_cents'],snapshot['discount_cents'],snapshot['total_cents'])==(11000,550,10450)
    monkeypatch.setitem(PLANS,'avancado',dict(PLANS['avancado'],price_cents=22000))
    assert pay(env,order['order_id'],amount=104.5)=={'ok':True}
    assert pay(env,order['order_id'],amount=104.5)=={'ok':True}
    with app.state.store.connect() as db:
        assert db.execute('SELECT used_count FROM sandbox_coupon_campaigns').fetchone()[0]==1
        assert json.loads(db.execute('SELECT snapshot FROM sandbox_coupon_redemptions').fetchone()[0])==snapshot
        assert db.execute('SELECT essay_credits FROM access_grants').fetchone()[0]==30
    with pytest.raises(HTTPException):app.state.coupons.quote('alice',code,'avancado')


@pytest.mark.parametrize('ending',['cancel','expire','rejected'])
def test_unpaid_order_releases_coupon_without_changing_issued_expiry(env,ending):
    app,_,clock=env;code=winner(env);oid=start(env,product='avancado',code=code)['order_id']
    if ending=='cancel':app.state.billing.cancel_sandbox('alice',oid)
    elif ending=='expire':clock[0]+=1800;app.state.billing.current('alice')
    else:pay(env,oid,status='rejected',amount=104.5)
    assert app.state.coupons.quote('alice',code,'avancado')['total_cents']==10450
    with app.state.store.connect() as db:
        assert db.execute('SELECT used_count FROM sandbox_coupon_campaigns').fetchone()[0]==0
        assert db.execute('SELECT expires_at FROM sandbox_coupons').fetchone()[0]>clock[0]+80*86400


def test_campaign_capacity_includes_simultaneous_holds(env):
    app,_,_=env;alice=winner(env,cap=1);bob=winner(env,uid='bob',cap=1)
    def buy(pair):
        try:return start(env,uid=pair[0],product='avancado',code=pair[1])
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(buy,[('alice',alice),('bob',bob)]))
    assert sum(isinstance(r,dict) for r in results)==1 and 409 in results


def test_coupon_wrong_owner_essential_and_no_prize_never_create_order(env):
    app,_,clock=env;code=winner(env)
    for uid,product in [('bob','avancado'),('alice','essencial')]:
        with pytest.raises(HTTPException):start(env,uid=uid,product=product,code=code)
    from unittest.mock import patch
    with patch('backend.moirae.sandbox_coupons.secrets.randbelow',return_value=99):
        assert app.state.coupons.draw('bob','approved')['code'] is None
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM billing_orders').fetchone()[0]==0


def test_http_guards_and_signed_webhook_grant_only_verified_owner(env):
    app,fake,clock=env
    # HTTP auth uses actual time, whereas payment/domain timestamps use the test clock.
    c=TestClient(app,base_url=BASE,headers={'Origin':BASE});register(app,c)
    with app.state.store.connect() as db:uid=db.execute("SELECT id FROM users WHERE email='billing@example.test'").fetchone()[0]
    payload=dict(product='creditos-5',key=str(uuid.uuid4()))
    assert c.post('/api/sandbox/credit-packs/checkout',json=dict(payload,price=1)).status_code==422
    assert c.post('/api/sandbox/credit-packs/checkout',json=payload,headers={'X-CSRF-Token':'bad'}).status_code==403
    order=c.post('/api/sandbox/credit-packs/checkout',json=payload);assert order.status_code==200
    oid=order.json()['order_id'];pay(env,oid,'pending')
    fake.payments['100']['status']='approved'
    assert notify(c,clock,signature='ts=1,v1='+'0'*64).status_code==401
    assert app.state.wallet.snapshot(uid)['available']==0
    assert notify(c,clock).status_code==200 and c.get('/api/sandbox/wallet').json()['available']==5
    exported=app.state.accounts.export(uid,PASSWORD)
    assert len(exported['sandbox_orders'])==1


def test_pack_validity_is_not_invented_and_provider_uncertainty_never_retries(env):
    app,fake,_=env;app.state.billing.sandbox_orders.pack_validity_days=None
    with pytest.raises(HTTPException) as e:start(env)
    assert e.value.status_code==503
    app.state.billing.sandbox_orders.pack_validity_days=90
    def timeout(*args):raise RuntimeError('synthetic ambiguous network response')
    fake.preference=timeout;key=str(uuid.uuid4())
    with pytest.raises(RuntimeError):start(env,key=key)
    with pytest.raises(HTTPException) as e:start(env,key=key)
    assert e.value.status_code==409
    assert app.state.billing.current('alice')['orders'][0]['status']=='needs_review'


def test_purchased_lot_funds_existing_demo_and_refund_prevents_completion(env):
    app,_,clock=env
    app.state.essays.enabled=True;app.state.essays.clock=lambda:clock[0]
    plan=start(env,product='essencial')['order_id'];pay(env,plan,amount=44)
    pack=start(env)['order_id'];pay(env,pack,pid='101')
    essay=app.state.essays.submit('alice',str(uuid.uuid4()),'Educação e cidadania','Um texto de demonstração. '*20,funding='sandbox_wallet')
    assert app.state.wallet.snapshot('alice')['lots'][0]['reserved']==1
    assert app.state.essays.process('alice',essay['id'])['status']=='completed'
    assert app.state.essays.process('alice',essay['id'])['status']=='completed'
    assert app.state.wallet.snapshot('alice')['lots'][0]['consumed']==1
    second=app.state.essays.submit('alice',str(uuid.uuid4()),'Educação e cidadania','Outro texto demonstrativo. '*20,funding='sandbox_wallet')
    clock[0]+=1;assert pay(env,pack,'refunded',pid='101')['review_required']
    assert app.state.essays.process('alice',second['id'])['status']=='failed'
    assert app.state.wallet.snapshot('alice')['available']==0


def test_additive_migration_preserves_preexisting_orders_wallet_and_coupons(env):
    app,_,clock=env
    oid=start(env,product='essencial')['order_id'];pay(env,oid,amount=44)
    lid=app.state.wallet.grant('alice','legacy-test-lot',2,clock[0]+86400)
    code=winner(env)
    with app.state.store.connect(write=True) as db:
        old_order=dict(db.execute('SELECT * FROM billing_orders').fetchone())
        old_coupon=dict(db.execute('SELECT * FROM sandbox_coupons').fetchone())
        db.execute('DROP TABLE sandbox_coupon_holds')
        db.execute('DROP TABLE sandbox_order_contracts')
        db.execute('DELETE FROM schema_version WHERE version=15')
    before=app.state.wallet.snapshot('alice')
    Store(app.state.store.path);Store(app.state.store.path)
    assert app.state.wallet.snapshot('alice')==before
    with app.state.store.connect() as db:
        assert dict(db.execute('SELECT * FROM billing_orders').fetchone())==old_order
        assert dict(db.execute('SELECT * FROM sandbox_coupons').fetchone())==old_coupon
        assert db.execute('SELECT count(*) FROM sandbox_order_contracts').fetchone()[0]==0
        assert db.execute('SELECT version FROM schema_version WHERE version=15').fetchone()[0]==15


def test_payment_cannot_move_to_another_account_order(env):
    app,_,_=env;first=start(env)['order_id'];pay(env,first)
    other=start(env,uid='bob')['order_id']
    with pytest.raises(HTTPException) as exc:pay(env,other)
    assert exc.value.status_code==409
    assert app.state.wallet.snapshot('bob')['available']==0
    assert contract(env,other)['state']=='pending'


def test_verified_webhook_wins_race_with_lost_preference_response(env):
    app,fake,_=env
    def preference(order,plan,origin):
        pay(env,order['id'])
        raise RuntimeError('synthetic response lost after verified payment')
    fake.preference=preference
    with pytest.raises(RuntimeError):start(env)
    current=app.state.billing.current('alice')['orders'][0]
    assert current['status']=='approved' and current['contract']['state']=='fulfilled'
    assert app.state.wallet.snapshot('alice')['available']==5
