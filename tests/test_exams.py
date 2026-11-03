import uuid
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.moirae.app import create_app
from backend.moirae.catalog import BY_ID
from backend.moirae.quota import monthly_quota

BASE='http://localhost:8000'

@pytest.fixture
def setup(tmp_path):
    app=create_app(str(tmp_path/'db.sqlite3'),origin=BASE,secure=False)
    clock=[datetime(2026,11,3,12,tzinfo=timezone.utc).timestamp()]
    app.state.exams.clock=lambda:clock[0]
    app.state.practice.clock=app.state.exams.day_now
    c=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    login=c.post('/api/auth/register',json={'email':'exam@example.test','password':'senha-exclusiva-123','accept_terms':True,'adult_pilot':True})
    c.headers['X-CSRF-Token']=login.json()['csrf']
    token=app.state.mailer.messages[-1]['link'].split('#token=')[1]
    assert c.post('/api/auth/verify-email',json={'token':token}).status_code==200
    return app,c,clock


def start(c,day=1,key=None):return c.post('/api/exams/start',json={'day':day,'key':key or str(uuid.uuid4())})

def item(c,e,choice='a',flagged=False,revision=0,qid=None):
    return c.post(f"/api/exams/{e['id']}/item",json={'question_id':qid or e['items'][0]['question']['id'],'choice':choice,'flagged':flagged,'revision':revision})

def essay(c,e,text='Texto autoral para testar o salvamento.',revision=0):
    return c.post(f"/api/exams/{e['id']}/essay",json={'text':text,'revision':revision})

def finish(c,e):return c.post(f"/api/exams/{e['id']}/finish",json={})

def practice_answers(c,n):
    for _ in range(n):
        s=c.post('/api/practice/start',json={}).json();q=s['question']
        r=c.post('/api/practice/answer',json={'session_id':s['id'],'question_id':q['id'],'choice':BY_ID[q['id']].answer,'key':str(uuid.uuid4())})
        assert r.status_code==200,r.text


def test_start_charges_shared_quota_once_and_hides_answers(setup):
    app,c,clock=setup;key=str(uuid.uuid4());r=start(c,key=key);assert r.status_code==200
    e=r.json();assert e['quota']['used']==6 and len(e['items'])==6 and e['essay_prompt']
    assert 'answer' not in e['items'][0] and 'explanation' not in e['items'][0] and 'result' not in e
    assert start(c,key=key).json()['id']==e['id']
    assert start(c).json()['id']==e['id']
    assert start(c,day=2).status_code==409
    practice_answers(c,1)
    assert c.get('/api/practice/current').json()['quota']['used']==7


def test_save_revise_flag_resume_without_charge(setup):
    app,c,clock=setup;e=start(c).json()
    first=item(c,e,choice='b',flagged=True);assert first.status_code==200
    assert first.json()['items'][0]['revision']==1
    assert item(c,e,choice='b',flagged=True).status_code==200 # retry idêntico
    assert item(c,e,choice='c',revision=0).status_code==409
    second=item(c,e,choice='c',revision=1);assert second.json()['quota']['used']==6
    saved=c.get('/api/exams/current').json()['exam'];assert saved['items'][0]['choice']=='c'
    assert saved['items'][0]['flagged'] is False
    assert saved['deadline']==e['deadline']


def test_shared_clock_essay_and_no_late_changes(setup):
    app,c,clock=setup;e=start(c).json();deadline=e['deadline']
    assert deadline-int(clock[0])==1800
    assert essay(c,e).json()['essay_revision']==1
    assert essay(c,e,text='Outro texto',revision=0).status_code==409
    clock[0]=deadline-1
    assert item(c,e).json()['status']=='active'
    clock[0]=deadline
    late=essay(c,e,text='Texto fora do prazo',revision=1).json()
    assert late['status']=='expired' and late['essay']=='Texto autoral para testar o salvamento.'
    assert late['result']['essay_status']=='saved_without_correction'
    assert item(c,e,choice='b',revision=1).json()['items'][0]['choice']=='a'
    assert finish(c,e).json()['status']=='expired'
    assert c.get('/api/exams/current').json()['exam']['deadline']==deadline


def test_day_two_and_manual_finish(setup):
    _,c,_=setup;e=start(c,day=2).json()
    assert e['essay_prompt'] is None and e['deadline']-e['started_at']==900
    assert essay(c,e).status_code==422
    answer=BY_ID[e['items'][0]['question']['id']].answer
    assert item(c,e,choice=answer).status_code==200
    result=finish(c,e).json();assert result['result']==dict(correct=1,total=6,blank=5,essay_status='not_applicable')
    assert result['items'][0]['answer']==answer
    assert finish(c,e).json()['result']==result['result']
    assert item(c,e,choice='b',revision=1).json()['status']=='submitted'
    assert result['quota']['used']==6


def test_abandoned_exams_exhaust_month_and_idempotent_start_after_finish(setup):
    _,c,_=setup;key=str(uuid.uuid4());e=start(c,key=key).json();finish(c,e)
    assert start(c,key=key).json()['id']==e['id']
    for _ in range(4):e=start(c).json();finish(c,e)
    assert start(c).status_code==429
    assert c.get('/api/practice/current').json()['quota']['remaining']==0
    assert c.post('/api/practice/start',json={}).status_code==429


def test_month_boundary_brasilia_and_old_exam_charge(setup):
    app,c,clock=setup
    clock[0]=datetime(2026,12,1,2,59,tzinfo=timezone.utc).timestamp()
    e=start(c).json();assert e['quota']['period']=='2026-11' and e['quota']['used']==6
    clock[0]=datetime(2026,12,1,3,0,tzinfo=timezone.utc).timestamp()
    current=c.get('/api/exams/current').json()['exam']
    assert current['id']==e['id'] and current['quota']['period']=='2026-12' and current['quota']['used']==0
    assert item(c,e).json()['quota']['used']==0 # caderno debitado no mês de início
    assert current['quota']['resets_at']=='2027-01-01T03:00:00+00:00'


def test_account_isolation_csrf_and_input_validation(setup):
    app,c,_=setup;e=start(c).json();b=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    r=b.post('/api/auth/register',json={'email':'outro@example.test','password':'senha-exclusiva-123','accept_terms':True,'adult_pilot':True});b.headers['X-CSRF-Token']=r.json()['csrf']
    assert b.post('/api/auth/verify-email',json={'token':app.state.mailer.messages[-1]['link'].split('#token=')[1]}).status_code==200
    assert b.get('/api/exams/current').json()['exam'] is None
    assert item(b,e).status_code==404 and essay(b,e).status_code==404 and finish(b,e).status_code==404
    assert c.post('/api/exams/start',json={'day':1,'key':str(uuid.uuid4()),'duration':9999}).status_code==422
    assert c.post('/api/exams/start',json={'day':3,'key':str(uuid.uuid4())}).status_code==422
    assert c.post('/api/exams/start',json={'day':1,'key':str(uuid.uuid4())},headers={'X-CSRF-Token':'bad'}).status_code==403
    assert essay(c,e,text='a'*4001).status_code==422
    assert item(c,e,qid='outside').status_code==404


def test_concurrent_starts_only_charge_once(setup):
    app,c,_=setup;headers=dict(c.headers);cookies=dict(c.cookies)
    def send(_):
        with TestClient(app,base_url=BASE,headers=headers,cookies=cookies) as other:return start(other)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(send,range(4)))
    assert all(r.status_code==200 for r in results)
    assert len({r.json()['id'] for r in results})==1
    assert c.get('/api/practice/current').json()['quota']['used']==6


def test_practice_and_exam_compete_for_last_balance(setup):
    app,c,_=setup;practice_answers(c,24);headers=dict(c.headers);cookies=dict(c.cookies)
    s=c.post('/api/practice/start',json={}).json();q=s['question']
    def race(kind):
        with TestClient(app,base_url=BASE,headers=headers,cookies=cookies) as other:
            if kind=='exam':return start(other)
            return other.post('/api/practice/answer',json={'session_id':s['id'],'question_id':q['id'],'choice':'a','key':str(uuid.uuid4())})
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(race,['exam','practice']))
    assert sorted(r.status_code for r in results)==[200,429]
    assert c.get('/api/practice/current').json()['quota']['used'] in (25,30)


def test_essay_survives_restart_and_source_is_plain_text(setup):
    app,c,_=setup;e=start(c).json();text='<script>alert(1)</script>\nRedação com acentos: educação.'
    assert essay(c,e,text=text).json()['essay']==text
    fresh=create_app(app.state.store.path,origin=BASE,secure=False);fresh.state.exams.clock=app.state.exams.clock
    resumed=TestClient(fresh,base_url=BASE,cookies=dict(c.cookies)).get('/api/exams/current').json()['exam']
    assert resumed['essay']==text and resumed['essay_revision']==1 and resumed['deadline']==e['deadline']


def test_existing_baseline_is_preserved_on_extension(tmp_path):
    import sqlite3
    from backend.moirae.store import SCHEMA,Store
    from backend.moirae.service import Practice
    path=tmp_path/'legacy.sqlite3'
    # Schema anterior ao módulo de simulados: nenhuma tabela antiga é removida.
    old=SCHEMA[:SCHEMA.index('CREATE TABLE IF NOT EXISTS mock_exams')]+SCHEMA[SCHEMA.index('CREATE TABLE IF NOT EXISTS idempotency'):]
    db=sqlite3.connect(path);db.executescript(old)
    db.execute("INSERT INTO users VALUES('u','legacy@example.test','not-used',1)")
    db.execute("INSERT INTO practice_sessions VALUES('s','u','active',1)")
    for i in range(2):db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)',(str(i),'u','s',f'mat-{i+1:02d}','a',0,'2026-11-03',1))
    db.commit();db.close()
    store=Store(str(path));practice=Practice(store,clock=lambda:'2026-11-25')
    with store.connect() as db:
        assert practice.quota(db,'u')['used']==2
        assert practice.quota(db,'u')['remaining']==28
        assert {r[0] for r in db.execute('SELECT version FROM schema_version')}=={1,2,3}
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]==2
