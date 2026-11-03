import hashlib
import hmac
import time
import uuid
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.moirae.app import create_app
from backend.moirae.catalog import BY_ID
from backend.moirae.mercadopago import verify_signature,safe_checkout

BASE='http://localhost:8000';SECRET='synthetic-webhook-secret-for-unit-tests';PASSWORD='senha-exclusiva-123'

class FakeProvider:
    def __init__(self):self.payments={};self.calls=0
    def preference(self,order,plan,origin):
        self.calls+=1
        return {'preference_id':'fake-'+order['id'],'checkout_url':'https://sandbox.mercadopago.com.br/checkout/test'}
    def payment(self,payment_id):return self.payments[payment_id].copy()

@pytest.fixture
def setup(tmp_path):
    fake=FakeProvider();app=create_app(str(tmp_path/'db'),origin=BASE,secure=False,billing_provider=fake,billing_collector='123',billing_secret=SECRET)
    clock=[int(time.time())];app.state.billing.clock=lambda:clock[0]
    c=TestClient(app,base_url=BASE,headers={'Origin':BASE});register(app,c)
    return app,c,fake,clock


def register(app,c,email='billing@example.test'):
    r=c.post('/api/auth/register',json={'email':email,'password':PASSWORD,'accept_terms':True,'adult_pilot':True});assert r.status_code==201
    c.headers['X-CSRF-Token']=r.json()['csrf']
    token=app.state.mailer.messages[-1]['link'].split('#token=')[1]
    assert c.post('/api/auth/verify-email',json={'token':token}).status_code==200


def checkout(c,plan='essencial',key=None):return c.post('/api/billing/checkout',json={'plan':plan,'key':key or str(uuid.uuid4())})

def payment(fake,oid,clock,**updates):
    value={'id':100,'external_reference':oid,'currency_id':'BRL','collector_id':123,'transaction_amount':44,'transaction_amount_refunded':0,'live_mode':False,'status':'approved','date_last_updated':datetime.fromtimestamp(clock[0],timezone.utc).isoformat()}
    value.update(updates);fake.payments['100']=value


def notify(c,clock,signature=None,body_id=100):
    ts=str(clock[0]);manifest=f'id:100;request-id:test-request;ts:{ts};'
    signature=signature or 'ts='+ts+',v1='+hmac.new(SECRET.encode(),manifest.encode(),hashlib.sha256).hexdigest()
    return c.post('/api/billing/webhook?data.id=100',json={'type':'payment','data':{'id':body_id}},headers={'Origin':'https://provider.example.test','X-Request-ID':'test-request','X-Signature':signature})


def test_catalog_and_disabled_checkout(tmp_path):
    app=create_app(str(tmp_path/'db'),origin=BASE,secure=False);c=TestClient(app,base_url=BASE,headers={'Origin':BASE});register(app,c)
    catalog=c.get('/api/billing/plans').json();assert catalog['checkout_enabled'] is False
    assert [(p['price_cents'],p['essay_credits']) for p in catalog['plans']]==[(4400,10),(11000,30)]
    assert checkout(c).status_code==503 and c.get('/api/auth/me').json()['plan']=='free'
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM billing_orders').fetchone()[0]==0


def test_checkout_idempotent_and_no_client_price_or_role(setup):
    app,c,fake,clock=setup;key=str(uuid.uuid4());r=checkout(c,key=key);assert r.status_code==200
    assert checkout(c,key=key).json()==r.json() and fake.calls==1
    assert checkout(c,plan='avancado',key=key).status_code==409
    assert checkout(c).status_code==409
    assert c.post('/api/billing/checkout',json={'plan':'essencial','key':str(uuid.uuid4()),'price':1}).status_code==422
    assert c.get('/api/auth/me').json()['plan']=='free' # sem liberação pelo retorno do checkout
    assert c.get('/api/dashboard').status_code==403


def test_approved_grants_exactly_thirty_days_without_duplicate_credits(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock)
    assert notify(c,clock).status_code==200
    assert c.get('/api/auth/me').json()['plan']=='essencial'
    first=c.get('/api/billing/current').json()['access'];assert first['ends_at']==clock[0]+30*86400 and first['essay_credits']==10
    clock[0]+=60
    assert notify(c,clock).status_code==200
    assert c.get('/api/billing/current').json()['access']==first
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM access_grants').fetchone()[0]==1
    assert c.get('/api/dashboard').status_code==200
    assert checkout(c).status_code==409


def test_pending_does_not_grant_and_body_status_is_not_trusted(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock,status='pending')
    assert notify(c,clock).status_code==200
    assert c.get('/api/auth/me').json()['plan']=='free'


@pytest.mark.parametrize('override',[{'transaction_amount':1},{'currency_id':'USD'},{'collector_id':999},{'live_mode':True},{'external_reference':str(uuid.uuid4())}])
def test_payment_mismatch_rejected(setup,override):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock,**override)
    assert notify(c,clock).status_code==400
    assert c.get('/api/auth/me').json()['plan']=='free'


def test_signature_and_id_validation(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock)
    assert notify(c,clock,signature='ts=1,v1='+'0'*64).status_code==401
    assert notify(c,clock,body_id=101).status_code==400
    assert c.post('/api/billing/webhook',json={}).status_code==400


def test_refund_revokes_and_old_events_cannot_regrant(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock);notify(c,clock)
    initial=fake.payments['100'].copy();clock[0]+=10;payment(fake,oid,clock,status='refunded',transaction_amount_refunded=44)
    assert notify(c,clock).status_code==200 and c.get('/api/auth/me').json()['plan']=='free'
    fake.payments['100']=initial;assert notify(c,clock).status_code==200
    assert c.get('/api/auth/me').json()['plan']=='free'


def test_partial_refund_suspends_access(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock);notify(c,clock)
    clock[0]+=10;payment(fake,oid,clock,transaction_amount_refunded=5,status_detail='partially_refunded');notify(c,clock)
    assert c.get('/api/dashboard').status_code==403


def test_paid_questions_do_not_consume_free_quota_after_expiry(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock);notify(c,clock)
    for _ in range(31):
        s=c.post('/api/practice/start',json={}).json();q=s['question']
        r=c.post('/api/practice/answer',json={'session_id':s['id'],'question_id':q['id'],'choice':BY_ID[q['id']].answer,'key':str(uuid.uuid4())});assert r.status_code==200
    assert c.get('/api/practice/current').json()['quota']['unlimited'] is True
    e=c.post('/api/exams/start',json={'day':2,'key':str(uuid.uuid4())});assert e.status_code==200
    with app.state.store.connect(write=True) as db:db.execute('UPDATE access_grants SET ends_at=?',(int(time.time())-1,))
    q=c.get('/api/practice/current').json()['quota'];assert q['plan']=='free' and q['remaining']==30
    assert c.get('/api/dashboard').status_code==403
    notify(c,clock);assert c.get('/api/auth/me').json()['plan']=='free' # não estende um grant expirado


def test_avancado_and_refund_request_is_not_refund(setup):
    app,c,fake,clock=setup;oid=checkout(c,plan='avancado').json()['order_id'];payment(fake,oid,clock,transaction_amount=110);notify(c,clock)
    assert c.get('/api/billing/current').json()['access']['essay_credits']==30
    r=c.post('/api/billing/orders/'+oid+'/refund-request',json={'password':PASSWORD});assert r.status_code==200 and r.json()['within_initial_window'] is True
    assert c.get('/api/auth/me').json()['plan']=='avancado'
    clock[0]+=8*86400
    r=c.post('/api/billing/orders/'+oid+'/refund-request',json={'password':PASSWORD});assert r.status_code==200 and r.json()['within_initial_window'] is False
    assert c.post('/api/account/delete',json={'password':PASSWORD,'confirmation':'EXCLUIR'}).status_code==409


def test_orders_and_refund_requests_scoped_to_owner(setup):
    app,a,fake,clock=setup;oid=checkout(a).json()['order_id']
    b=TestClient(app,base_url=BASE,headers={'Origin':BASE});register(app,b,'other@example.test')
    assert b.get('/api/billing/current').json()['orders']==[]
    assert b.post('/api/billing/orders/'+oid+'/refund-request',json={'password':PASSWORD}).status_code==404


def test_checkout_url_rejects_arbitrary_destinations():
    from fastapi import HTTPException
    with pytest.raises(HTTPException):safe_checkout('https://evil.test/pay')
    with pytest.raises(HTTPException):safe_checkout('javascript:alert(1)')


def test_concurrent_notifications_do_not_extend_period(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock)
    def send(_):
        with TestClient(app,base_url=BASE) as other:return notify(other,clock).status_code
    with ThreadPoolExecutor(max_workers=4) as pool:assert list(pool.map(send,range(4)))==[200]*4
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM access_grants').fetchone()[0]==1
        assert db.execute('SELECT ends_at-starts_at FROM access_grants').fetchone()[0]==30*86400


def test_provider_failure_never_grants_and_refund_does_not_delete_records(setup):
    from fastapi import HTTPException
    app,c,fake,clock=setup
    def failed(*args):raise HTTPException(503,'Indisponível')
    fake.preference=failed
    assert checkout(c).status_code==503
    assert c.get('/api/auth/me').json()['plan']=='free'
    with app.state.store.connect() as db:
        assert db.execute('SELECT status FROM billing_orders').fetchone()[0]=='failed'
        assert db.execute('SELECT count(*) FROM access_grants').fetchone()[0]==0


def test_dashboard_uses_own_data_and_access_is_revoked_on_chargeback(setup):
    app,c,fake,clock=setup;oid=checkout(c).json()['order_id'];payment(fake,oid,clock);notify(c,clock)
    s=c.post('/api/practice/start',json={}).json();q=s['question']
    c.post('/api/practice/answer',json={'session_id':s['id'],'question_id':q['id'],'choice':BY_ID[q['id']].answer,'key':str(uuid.uuid4())})
    dash=c.get('/api/dashboard').json();assert dash['answered']==1 and dash['correct']==1 and dash['accuracy']==100
    clock[0]+=10;payment(fake,oid,clock,status='charged_back');assert notify(c,clock).status_code==200
    assert c.get('/api/dashboard').status_code==403


def test_http_adapter_uses_server_price_and_sandbox_destination(monkeypatch):
    import json
    import httpx
    import backend.moirae.mercadopago as mp
    from backend.moirae.plans import PLANS
    real_client=httpx.Client;seen=[]
    def handle(request):
        seen.append(request)
        return httpx.Response(200,json={'id':'preference-test','sandbox_init_point':'https://sandbox.mercadopago.com.br/checkout/test'})
    monkeypatch.setattr(mp.httpx,'Client',lambda **kwargs:real_client(transport=httpx.MockTransport(handle),**kwargs))
    result=mp.MercadoPagoSandbox('TEST-synthetic').preference({'id':'server-order'},PLANS['essencial'],'https://moirae.example.test')
    assert result['checkout_url'].startswith('https://sandbox.')
    payload=json.loads(seen[0].content);assert payload['items'][0]['unit_price']==44 and payload['items'][0]['quantity']==1
    assert payload['external_reference']=='server-order' and payload['notification_url'].startswith('https://moirae.example.test/api/billing/webhook')
    assert seen[0].headers['authorization']=='Bearer TEST-synthetic'


def test_signature_supports_milliseconds_and_rejects_bad_mac():
    from fastapi import HTTPException
    now=1700000000;ts=str(now*1000);manifest=f'id:100;request-id:test-request;ts:{ts};'
    signature=hmac.new(SECRET.encode(),manifest.encode(),hashlib.sha256).hexdigest()
    verify_signature('100','test-request',f'ts={ts}, v1={signature}',SECRET,now)
    with pytest.raises(HTTPException):verify_signature('100','test-request',f'ts={ts},v1={"0"*64}',SECRET,now)



def test_order_contract_survives_catalog_change(setup, monkeypatch):
    from backend.moirae.plans import PLANS
    app,c,fake,clock=setup
    oid=checkout(c).json()['order_id']
    monkeypatch.setitem(PLANS,'essencial',dict(PLANS['essencial'],essay_credits=99,days=90))
    payment(fake,oid,clock)
    assert notify(c,clock).status_code==200
    access=c.get('/api/billing/current').json()['access']
    assert access['essay_credits']==10 and access['ends_at']==clock[0]+30*86400


@pytest.mark.parametrize('plan,amount,credits',[('essencial',3500,3),('avancado',5500,8)])
def test_legacy_pending_order_migrates_without_changing_contract(setup,plan,amount,credits):
    from backend.moirae.store import Store
    app,c,fake,clock=setup
    oid=checkout(c,plan=plan).json()['order_id']
    with app.state.store.connect(write=True) as db:
        db.execute('UPDATE billing_orders SET amount_cents=?,essay_credits=NULL,access_days=NULL,catalog_version=NULL WHERE id=?',(amount,oid))
    Store(app.state.store.path)
    payment(fake,oid,clock,transaction_amount=amount/100)
    assert notify(c,clock).status_code==200
    access=c.get('/api/billing/current').json()['access']
    assert access['essay_credits']==credits
    Store(app.state.store.path)
    assert c.get('/api/billing/current').json()['access']==access


def test_unknown_legacy_contract_cannot_grant_access(setup):
    app,c,fake,clock=setup
    oid=checkout(c).json()['order_id']
    with app.state.store.connect(write=True) as db:
        db.execute('UPDATE billing_orders SET catalog_version=NULL WHERE id=?',(oid,))
    payment(fake,oid,clock)
    assert notify(c,clock).status_code==409
    assert c.get('/api/auth/me').json()['plan']=='free'


def test_schema_six_adds_contract_columns_to_existing_database(tmp_path):
    import sqlite3
    from backend.moirae.store import SCHEMA,Store
    path=str(tmp_path/'legacy.sqlite3')
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA)
        db.execute("INSERT INTO users VALUES('u','legacy@example.test','not-a-real-hash',1)")
        db.execute("INSERT INTO billing_orders(id,user_id,plan_id,amount_cents,status,created_at,request_key) VALUES('legacy','u','avancado',5500,'pending',1,'old')")
        db.execute("INSERT INTO access_grants VALUES('legacy','u','avancado',1,9999999999,'active',8)")
    migrated=Store(path)
    with migrated.connect() as db:
        row=db.execute("SELECT * FROM billing_orders WHERE id='legacy'").fetchone()
        assert (row['catalog_version'],row['essay_credits'],row['access_days'])==(1,8,30)
        assert db.execute('SELECT essay_credits FROM access_grants').fetchone()[0]==8
    Store(path)


@pytest.mark.parametrize('plan,old_amount,credits',[('essencial',4000,10),('avancado',10000,30)])
def test_version_two_orders_keep_price_after_ten_percent_markup(setup,plan,old_amount,credits):
    app,c,fake,clock=setup;oid=checkout(c,plan=plan).json()['order_id']
    with app.state.store.connect(write=True) as db:
        db.execute('UPDATE billing_orders SET amount_cents=?,catalog_version=2 WHERE id=?',(old_amount,oid))
    payment(fake,oid,clock,transaction_amount=old_amount/100)
    assert notify(c,clock).status_code==200
    assert c.get('/api/billing/current').json()['access']['essay_credits']==credits
