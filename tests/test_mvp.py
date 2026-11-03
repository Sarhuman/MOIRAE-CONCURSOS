import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.moirae.app import create_app
from backend.moirae.catalog import BY_ID
from backend.moirae.domain import study_day

@pytest.fixture
def env(tmp_path):
    app=create_app(str(tmp_path/'db.sqlite3'),origin='http://localhost:8000',secure=False)
    return app,TestClient(app,base_url='http://localhost:8000',headers={'Origin':'http://localhost:8000'})

def register(c,email='aluno@example.test'):
    r=c.post('/api/auth/register',json={'email':email,'password':'senha-exclusiva-123'})
    assert r.status_code==201,r.text
    c.headers['X-CSRF-Token']=r.json()['csrf'];return r

def answer(c,s,key=None,choice=None):
    q=s['question'];return c.post('/api/practice/answer',json={'session_id':s['id'],'question_id':q['id'],'choice':choice or BY_ID[q['id']].answer,'key':key or str(uuid.uuid4())})

def complete(c):
    s=c.post('/api/practice/start',json={}).json()
    while s['status']=='active':
        r=answer(c,s);assert r.status_code==200,r.text;s=r.json()['session']
    return s

def test_flow_persistence_and_revocation(env):
    app,c=env;register(c);s=c.post('/api/practice/start',json={}).json()
    assert s==c.post('/api/practice/start',json={}).json()
    assert 'answer' not in s['question'] and 'explanation' not in s['question']
    assert answer(c,s).json()['session']['quota']['remaining']==29
    old=dict(c.cookies);assert c.post('/api/auth/logout',json={}).status_code==200
    assert TestClient(app,base_url='http://localhost:8000',cookies=old).get('/api/auth/me').status_code==401
    r=c.post('/api/auth/login',json={'email':'ALUNO@example.test','password':'senha-exclusiva-123'});assert r.status_code==200
    c.headers['X-CSRF-Token']=r.json()['csrf']
    other=create_app(app.state.store.path,origin='http://localhost:8000',secure=False)
    r=TestClient(other,base_url='http://localhost:8000',cookies=dict(c.cookies)).get('/api/practice/current')
    assert r.json()['session']['answered']==1 and r.json()['session']['id']==s['id']

def test_idempotency_and_conflict(env):
    _,c=env;register(c);s=c.post('/api/practice/start',json={}).json();key=str(uuid.uuid4())
    r=answer(c,s,key);assert answer(c,s,key).json()==r.json()
    assert answer(c,s).status_code==409
    different='a' if BY_ID[s['question']['id']].answer!='a' else 'b'
    assert answer(c,s,key,different).status_code==409
    assert c.get('/api/practice/current').json()['quota']['used']==1

def test_limit_and_renewal(env):
    app,c=env;register(c);app.state.practice.clock=lambda:'2026-11-03'
    for _ in range(6):complete(c)
    assert c.post('/api/practice/start',json={}).status_code==429
    app.state.practice.clock=lambda:'2026-11-04'
    assert c.get('/api/practice/current').json()['quota']['remaining']==0
    app.state.practice.clock=lambda:'2026-12-01'
    assert c.get('/api/practice/current').json()['quota']['remaining']==30
    assert c.post('/api/practice/start',json={}).status_code==200

def test_isolation_and_premium(env):
    app,a=env;register(a);s=a.post('/api/practice/start',json={}).json()
    b=TestClient(app,base_url='http://localhost:8000',headers={'Origin':'http://localhost:8000'});register(b,'outro@example.test')
    assert answer(b,s).status_code==404
    assert b.get('/api/dashboard').status_code==403
    assert TestClient(app).get('/api/practice/current').status_code==401

def test_origin_csrf_secret_and_path(env):
    _,c=env;register(c)
    assert c.post('/api/practice/start',json={},headers={'Origin':'https://evil.test'}).status_code==403
    assert c.post('/api/practice/start',json={},headers={'X-CSRF-Token':'wrong'}).status_code==403
    r=c.post('/api/auth/register',json={'email':'bad','password':'secret'})
    assert r.status_code==422 and 'secret' not in r.text
    assert c.get('/assets/../backend/moirae/app.py').status_code==404
    assert c.get('/styles.css?filename=/etc/passwd').headers['content-type'].startswith('text/css')

def test_concurrent_retry(env):
    app,c=env;register(c);s=c.post('/api/practice/start',json={}).json();key=str(uuid.uuid4());cookies=dict(c.cookies);headers=dict(c.headers)
    def send(_):
        with TestClient(app,base_url='http://localhost:8000',headers=headers,cookies=cookies) as client:return answer(client,s,key)
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(send,range(5)))
    assert all(r.status_code==200 for r in results)
    assert all(r.json()==results[0].json() for r in results)
    assert c.get('/api/practice/current').json()['quota']['used']==1

def test_rate_limit(env):
    _,c=env
    for _ in range(10):assert c.post('/api/auth/login',json={'email':'same@example.test','password':'senha-exclusiva-123'}).status_code==401
    assert c.post('/api/auth/login',json={'email':'same@example.test','password':'senha-exclusiva-123'}).status_code==429

def test_hash_cookie_and_expiry(env):
    app,c=env;r=register(c);assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
    with app.state.store.connect(write=True) as db:
        assert db.execute('SELECT password_hash FROM users').fetchone()[0].startswith('$argon2id$')
        assert len(db.execute('SELECT token_hash FROM auth_sessions').fetchone()[0])==64
        db.execute('UPDATE auth_sessions SET expires_at=0')
    assert c.get('/api/auth/me').status_code==401

def test_brasilia_midnight():
    assert study_day(datetime(2026,11,4,2,59,tzinfo=timezone.utc))=='2026-11-03'
    assert study_day(datetime(2026,11,4,3,0,tzinfo=timezone.utc))=='2026-11-04'

def test_last_quota_concurrency(env):
    app,c=env;register(c)
    for _ in range(5):complete(c)
    s=c.post('/api/practice/start',json={}).json()
    for _ in range(4):s=answer(c,s).json()['session']
    cookies=dict(c.cookies);headers=dict(c.headers)
    def send(_):
        with TestClient(app,base_url='http://localhost:8000',headers=headers,cookies=cookies) as client:return answer(client,s)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(send,range(2)))
    assert sorted(r.status_code for r in results)==[200,409]
    assert c.get('/api/practice/current').json()['quota']['used']==30


def test_payload_limits_and_cookie_secure(tmp_path):
    app=create_app(str(tmp_path/'secure.sqlite3'),origin='https://example.test',secure=True)
    c=TestClient(app,base_url='https://example.test',headers={'Origin':'https://example.test'})
    r=register(c);assert '__Host-moirae=' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
    assert c.post('/api/auth/login',content='x'*20000).status_code==413
    assert c.post('/api/auth/login',content='x'*20000,headers={'Content-Length':'1'}).status_code==413


def test_wrong_answer_and_future_question(env):
    _,c=env;register(c);s=c.post('/api/practice/start',json={}).json()
    wrong='a' if BY_ID[s['question']['id']].answer!='a' else 'b'
    r=answer(c,s,choice=wrong);assert r.json()['correct'] is False and r.json()['explanation']
    assert r.json()['session']['answered']==1
