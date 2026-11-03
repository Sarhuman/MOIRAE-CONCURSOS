import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.moirae.app import create_app
from backend.moirae.catalog import BY_ID

BASE='http://localhost:8000'; PASSWORD='senha-exclusiva-123'

def register(app,email):
    c=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    r=c.post('/api/auth/register',json=dict(email=email,password=PASSWORD,accept_terms=True,adult_pilot=True));assert r.status_code==201
    c.headers['X-CSRF-Token']=r.json()['csrf']
    assert c.post('/api/auth/verify-email',json={'token':app.state.mailer.messages[-1]['link'].split('#token=')[1]}).status_code==200
    with app.state.store.connect() as db:uid=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()[0]
    return c,uid

def grant(app,uid):
    now=int(time.time());oid=str(uuid.uuid4())
    with app.state.store.connect(write=True) as db:
        db.execute("INSERT INTO billing_orders(id,user_id,plan_id,amount_cents,status,created_at,request_key) VALUES(?,?,'essencial',4000,'approved',?,?)",(oid,uid,now,oid))
        db.execute("INSERT INTO access_grants VALUES(?,?,'essencial',?,?,'active',10)",(oid,uid,now-1,now+86400))

@pytest.fixture
def setup(tmp_path):
    app=create_app(str(tmp_path/'db'),origin=BASE,secure=False)
    c,uid=register(app,'review@example.test');grant(app,uid)
    return app,c,uid

def answer(c,correct=False):
    s=c.post('/api/practice/start',json={}).json();q=s['question'];choice=BY_ID[q['id']].answer
    if not correct:choice=next(x for x in 'abcde' if x!=choice)
    assert c.post('/api/practice/answer',json=dict(session_id=s['id'],question_id=q['id'],choice=choice,key=str(uuid.uuid4()))).status_code==200
    return q['id']

def test_private_review_and_favorite_are_idempotent(setup):
    app,c,uid=setup;qid=answer(c)
    data=c.get('/api/review').json();assert len(data['items'])==1 and data['items'][0]['had_error']
    assert data['items'][0]['answer']==BY_ID[qid].answer
    with app.state.store.connect() as db:before=db.execute('SELECT count(*) FROM attempts').fetchone()[0]
    for _ in range(2):assert c.post(f'/api/review/{qid}/favorite',json={'enabled':True}).status_code==200
    assert len(c.get('/api/review?view=favorites').json()['items'])==1
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM review_favorites').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]==before
    assert c.post(f'/api/review/{qid}/favorite',json={'enabled':False}).status_code==200
    assert c.get('/api/review?view=favorites').json()['items']==[]


def test_no_answer_or_other_student_data_leaked(setup):
    app,c,uid=setup;qid=answer(c)
    b,bid=register(app,'other-review@example.test');grant(app,bid)
    assert b.get('/api/review?view=all').json()['items']==[]
    assert b.post(f'/api/review/{qid}/favorite',json={'enabled':True}).status_code==404
    unseen=next(q for q in BY_ID if q!=qid)
    assert c.post(f'/api/review/{unseen}/favorite',json={'enabled':True}).status_code==404
    assert c.post('/api/review/unknown/favorite',json={'enabled':True}).status_code==404


def test_free_expired_and_unauthenticated_are_blocked(setup):
    app,c,uid=setup;qid=answer(c)
    guest=TestClient(app,base_url=BASE)
    assert guest.get('/api/review').status_code==401
    with app.state.store.connect(write=True) as db:db.execute('UPDATE access_grants SET ends_at=?',(int(time.time())-1,))
    assert c.get('/api/review').status_code==403
    assert c.post(f'/api/review/{qid}/favorite',json={'enabled':True}).status_code==403


def test_csrf_origin_and_strict_input(setup):
    app,c,uid=setup;qid=answer(c)
    path=f'/api/review/{qid}/favorite'
    assert c.post(path,json={'enabled':True},headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert c.post(path,json={'enabled':True},headers={'Origin':'https://evil.example'}).status_code==403
    assert c.post(path,json={'enabled':'true'}).status_code==422
    assert c.get('/api/review?view=unknown').status_code==422


def test_favorites_export_and_persist_after_reopen(setup):
    app,c,uid=setup;qid=answer(c,True)
    assert c.get('/api/review').json()['items']==[]
    c.post(f'/api/review/{qid}/favorite',json={'enabled':True})
    exported=c.post('/api/account/export',json={'password':PASSWORD})
    assert exported.status_code==200 and exported.json()['favorites']==[{'question_id':qid}]
    from backend.moirae.review import Review
    from backend.moirae.store import Store
    assert Review(Store(app.state.store.path)).listing(uid,'favorites')['items'][0]['question']['id']==qid


def test_latest_success_keeps_previous_error(setup):
    app,c,uid=setup;qid=answer(c)
    with app.state.store.connect(write=True) as db:
        original=db.execute('SELECT * FROM attempts WHERE user_id=?',(uid,)).fetchone()
        sid=str(uuid.uuid4())
        db.execute("INSERT INTO practice_sessions VALUES(?,?,'completed',?)",(sid,uid,int(time.time())+1))
        db.execute('INSERT INTO attempts(id,user_id,session_id,question_id,choice,correct,day,created_at,free_charge) VALUES(?,?,?,?,?,1,?,?,0)',(str(uuid.uuid4()),uid,sid,qid,BY_ID[qid].answer,original['day'],int(time.time())+1))
    item=c.get('/api/review').json()['items'][0]
    assert item['had_error'] and item['last_correct'] and len(c.get('/api/review').json()['items'])==1


def test_concurrent_favorites_do_not_duplicate(setup):
    app,c,uid=setup;qid=answer(c)
    from backend.moirae.review import Review
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:Review(app.state.store).favorite(uid,qid,True),range(4)))
    assert len(c.get('/api/review?view=favorites').json()['items'])==1


def test_account_deletion_removes_preserved_favorites(tmp_path):
    app=create_app(str(tmp_path/'db'),origin=BASE,secure=False)
    c,uid=register(app,'delete-review@example.test');qid=answer(c)
    # Simulate preserved favorites after a previous access without financial records.
    with app.state.store.connect(write=True) as db:
        db.execute('INSERT INTO review_favorites VALUES(?,?)',(uid,qid))
    assert c.post('/api/account/delete',json={'password':PASSWORD,'confirmation':'EXCLUIR'}).status_code==200
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM review_favorites WHERE user_id=?',(uid,)).fetchone()[0]==0
