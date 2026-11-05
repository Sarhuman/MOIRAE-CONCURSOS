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
    r=c.post('/api/auth/register',json={'email':email,'password':'senha-exclusiva-123','accept_terms':True,'adult_pilot':True})
    assert r.status_code==201,r.text
    c.headers['X-CSRF-Token']=r.json()['csrf']
    token=c.app.state.mailer.messages[-1]['link'].split('#token=')[1]
    assert c.post('/api/auth/verify-email',json={'token':token}).status_code==200
    return r

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
    from backend.moirae.mail import LocalMail
    app=create_app(str(tmp_path/'secure.sqlite3'),origin='https://example.test',secure=True,mailer=LocalMail(tmp_path/'outbox'))
    c=TestClient(app,base_url='https://example.test',headers={'Origin':'https://example.test'})
    r=register(c);assert '__Host-moirae=' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
    assert c.post('/api/auth/login',content='x'*20000).status_code==413
    assert c.post('/api/auth/login',content='x'*20000,headers={'Content-Length':'1'}).status_code==413


def test_wrong_answer_and_future_question(env):
    _,c=env;register(c);s=c.post('/api/practice/start',json={}).json()
    wrong='a' if BY_ID[s['question']['id']].answer!='a' else 'b'
    r=answer(c,s,choice=wrong);assert r.json()['correct'] is False and r.json()['explanation']
    assert r.json()['session']['answered']==1

def test_five_questions_finish_without_restart(env):
    app,c=env
    register(c)
    session=c.post('/api/practice/start',json={}).json()
    original=session['id'];seen=[]
    assert session['total']==5
    for index in range(5):
        seen.append(session['question']['id'])
        response=answer(c,session)
        assert response.status_code==200
        result=response.json();session=result['session']
        assert session['answered']==index+1
    assert len(set(seen))==5
    assert session['status']=='completed' and session['question'] is None
    assert result['summary']['total']==5
    for _ in range(2):
        assert c.get('/api/practice/current').json()['session'] is None
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM practice_sessions').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM attempts WHERE session_id=?',(original,)).fetchone()[0]==5

def test_initial_diagnostic_is_private_durable_and_covers_four_areas(env):
    app,c=env
    register(c)
    assert c.get('/api/diagnostic').json()['status']=='not_started'
    s=c.post('/api/diagnostic/start',json={}).json()
    areas=set()
    assert c.post('/api/diagnostic/start',json={}).json()['id']==s['id']
    for _ in range(5):
        areas.add(s['question']['area'])
        assert c.get('/api/diagnostic').json()['areas']==[]
        q=BY_ID[s['question']['id']]
        wrong=next(chr(97+i) for i in range(5) if chr(97+i)!=q.answer)
        s=answer(c,s,choice=wrong).json()['session']
    assert len(areas)==4
    result=c.get('/api/diagnostic').json()
    assert result['status']=='completed' and result['focus']
    assert sum(a['errors'] for a in result['areas'])==5
    assert c.get('/api/practice/current').json()['session'] is None
    register(c,'other-diagnostic@example.test')
    assert c.get('/api/diagnostic').json()['status']=='not_started'

def test_diagnostic_respects_existing_activity_and_all_correct(env):
    _,c=env;register(c)
    s=c.post('/api/practice/start',json={}).json()
    assert c.post('/api/diagnostic/start',json={}).status_code==409
    while s['status']=='active':s=answer(c,s).json()['session']
    s=c.post('/api/diagnostic/start',json={}).json()
    while s['status']=='active':s=answer(c,s).json()['session']
    d=c.get('/api/diagnostic').json()
    assert d['status']=='completed' and d['focus'] is None
    assert sum(a['errors'] for a in d['areas'])==0

def test_validated_official_block_sources_answers_and_resume(env):
    _,c=env;register(c)
    s=c.post('/api/practice/enem-2025/start',json={}).json();sid=s['id']
    assert s['total']==4
    assert c.post('/api/practice/enem-2025/start',json={}).json()['id']==sid
    numbers=[]
    while s['status']=='active':
        q=s['question'];numbers.append(q['provenance']['number'])
        assert 'answer' not in q and 'explanation' not in q
        assert q['provenance']['visual_review']
        r=answer(c,s).json();assert r['correct'];assert len(r['alternatives'])==5
        s=r['session']
    assert numbers==[136,137,144,146]
    assert r['summary']['correct']==4
    assert c.get('/api/practice/current').json()['session'] is None

def test_second_official_batch_and_explanations(env):
    _,c=env;register(c)
    s=c.post('/api/practice/enem-2025/batch-2/start',json={}).json();seen=[]
    assert s['total']==4
    while s['status']=='active':
        q=s['question'];seen.append(q['provenance']['number'])
        assert q['provenance']['batch']==2 and 'answer' not in q
        r=answer(c,s).json();assert r['correct'];assert len(r['alternatives'])==5
        s=r['session']
    assert seen==[150,151,152,154]
    assert r['summary']['correct']==4
    assert c.get('/api/practice/current').json()['session'] is None

def test_third_official_batch_and_explanations(env):
    _,c=env;register(c)
    s=c.post('/api/practice/enem-2025/batch-3/start',json={}).json();seen=[]
    assert s['total']==5
    assert c.post('/api/practice/enem-2025/batch-3/start',json={}).json()['id']==s['id']
    while s['status']=='active':
        q=s['question'];seen.append(q['provenance']['number'])
        assert q['provenance']['batch']==3 and 'answer' not in q
        r=answer(c,s).json();assert r['correct'];assert len(r['alternatives'])==5
        s=r['session']
    assert seen==[155,156,157,158,159]
    assert r['summary']['correct']==5
    assert c.get('/api/practice/current').json()['session'] is None

def test_fourth_official_batch_and_explanations(env):
    _,c=env;register(c)
    s=c.post('/api/practice/enem-2025/batch-4/start',json={}).json();seen=[]
    assert s['total']==4
    assert c.post('/api/practice/enem-2025/batch-4/start',json={}).json()['id']==s['id']
    while s['status']=='active':
        q=s['question'];seen.append(q['provenance']['number'])
        assert q['provenance']['batch']==4 and 'answer' not in q
        r=answer(c,s).json();assert r['correct'];assert len(r['alternatives'])==5
        s=r['session']
    assert seen==[162,163,165,166]
    assert r['summary']['correct']==4
    assert c.get('/api/practice/current').json()['session'] is None

def test_fifth_official_batch_and_explanations(env):
    _,c=env;register(c)
    s=c.post('/api/practice/enem-2025/batch-5/start',json={}).json();seen=[]
    assert s['total']==3
    assert c.post('/api/practice/enem-2025/batch-5/start',json={}).json()['id']==s['id']
    while s['status']=='active':
        q=s['question'];seen.append(q['provenance']['number'])
        assert q['provenance']['batch']==5 and 'answer' not in q
        r=answer(c,s).json();assert r['correct'];assert len(r['alternatives'])==5
        s=r['session']
    assert seen==[167,168,169]
    assert r['summary']['correct']==3
    assert c.get('/api/practice/current').json()['session'] is None


def test_diagnostic_low_quota_does_not_create_partial_session(env):
    app,c=env;register(c)
    for _ in range(6):complete(c)
    with app.state.store.connect(write=True) as db:
        db.execute('DELETE FROM attempts WHERE id IN (SELECT id FROM attempts LIMIT 4)')
        before=db.execute('SELECT count(*) FROM practice_sessions').fetchone()[0]
    r=c.post('/api/diagnostic/start',json={})
    assert r.status_code==429
    assert c.get('/api/practice/current').json()['quota']['remaining']==4
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM practice_sessions').fetchone()[0]==before
        assert db.execute('SELECT count(*) FROM diagnostic_sessions').fetchone()[0]==0

def test_diagnostic_covers_four_areas_with_introductory_items(env):
    app,c=env;register(c)
    s=c.post('/api/diagnostic/start',json={}).json();areas=set()
    assert s['total']==5
    while s['status']=='active':
        assert not s['question'].get('provenance')
        areas.add(s['question']['area'])
        s=answer(c,s).json()['session']
    assert len(areas)==4
    assert c.get('/api/diagnostic').json()['answered']==5
