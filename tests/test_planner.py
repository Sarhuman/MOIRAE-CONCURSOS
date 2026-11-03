import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_review import setup, register, answer, grant, BASE
from fastapi.testclient import TestClient
from backend.moirae.catalog import BY_ID,QUESTIONS
from backend.moirae.planner import record_answer,selection,DAY


def test_intervals_reset_and_cap(setup):
    app,c,uid=setup;now=int(time.time());qid=QUESTIONS[0].id
    with app.state.store.connect(write=True) as db:
        record_answer(db,uid,qid,True,now)
        assert db.execute('SELECT count(*) FROM review_schedule').fetchone()[0]==0
        record_answer(db,uid,qid,False,now)
        assert db.execute('SELECT due_at FROM review_schedule').fetchone()[0]==now+DAY
        for i,days in enumerate((3,7,14,30,30)):
            record_answer(db,uid,qid,True,now+i+1)
            row=db.execute('SELECT * FROM review_schedule').fetchone()
            assert row['due_at']==now+i+1+days*DAY
        record_answer(db,uid,qid,False,now+20)
        row=db.execute('SELECT * FROM review_schedule').fetchone()
        assert row['stage']==0 and row['due_at']==now+20+DAY


@pytest.mark.parametrize('minutes,size',[(15,3),(30,6),(60,12)])
def test_planned_session_sizes_no_answer_leak_and_resume(setup,minutes,size):
    app,c,uid=setup
    preview=c.get(f'/api/planner?minutes={minutes}');assert preview.status_code==200
    assert preview.json()['question_count']==min(size,len(QUESTIONS))
    s=c.post('/api/planner/start',json={'minutes':minutes}).json()
    assert s['total']==min(size,len(QUESTIONS)) and s['plan']['minutes']==minutes
    assert 'answer' not in s['question'] and 'explanation' not in s['question']
    again=c.post('/api/planner/start',json={'minutes':15}).json()
    assert again['id']==s['id'] and again['total']==s['total']


def test_due_first_and_future_review_excluded(setup):
    app,c,uid=setup;now=int(time.time());a,b=QUESTIONS[:2]
    with app.state.store.connect(write=True) as db:
        db.execute('INSERT INTO review_schedule VALUES(?,?,0,?,?)',(uid,a.id,now-1,now-2*DAY))
        db.execute('INSERT INTO review_schedule VALUES(?,?,0,?,?)',(uid,b.id,now+DAY,now))
        chosen,plan=selection(db,uid,30,now)
    assert chosen[0].id==a.id and b.id not in [q.id for q in chosen]
    assert plan['due_reviews']==1 and plan['next_review_at']==now+DAY


def test_answer_updates_schedule_once_with_repeated_key(setup):
    app,c,uid=setup;s=c.post('/api/planner/start',json={'minutes':15}).json();q=s['question']
    wrong=next(x for x in 'abcde' if x!=BY_ID[q['id']].answer)
    payload=dict(session_id=s['id'],question_id=q['id'],choice=wrong,key=str(uuid.uuid4()))
    first=c.post('/api/practice/answer',json=payload);assert first.status_code==200
    assert first.json()['review_schedule']['stage']==0
    with app.state.store.connect() as db:before=dict(db.execute('SELECT * FROM review_schedule').fetchone())
    assert c.post('/api/practice/answer',json=payload).status_code==200
    with app.state.store.connect() as db:
        assert dict(db.execute('SELECT * FROM review_schedule').fetchone())==before
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]==1


def test_access_csrf_and_invalid_duration(setup):
    app,c,uid=setup
    assert c.get('/api/planner?minutes=20').status_code==422
    assert c.post('/api/planner/start',json={'minutes':20}).status_code==422
    assert c.post('/api/planner/start',json={'minutes':True}).status_code==422
    assert c.post('/api/planner/start',json={'minutes':15},headers={'X-CSRF-Token':'bad'}).status_code==403
    assert TestClient(app,base_url=BASE).get('/api/planner').status_code==401
    other,other_id=register(app,'free-planner@example.test')
    assert other.get('/api/planner').status_code==403
    assert other.post('/api/planner/start',json={'minutes':15}).status_code==403
    with app.state.store.connect(write=True) as db:db.execute('UPDATE access_grants SET ends_at=?',(int(time.time())-1,))
    assert c.get('/api/planner').status_code==403


def test_schedule_is_private_and_exported(setup):
    from test_review import PASSWORD
    app,c,uid=setup;answer(c)
    other,other_id=register(app,'private-planner@example.test');grant(app,other_id)
    assert other.get('/api/planner').json()['next_review_at'] is None
    data=c.post('/api/account/export',json={'password':PASSWORD}).json()
    assert len(data['review_schedule'])==1


def test_concurrent_starts_have_one_session(setup):
    from backend.moirae.service import Practice
    app,c,uid=setup
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:Practice(app.state.store).start(uid,30),range(4)))
    assert len({r['id'] for r in results})==1
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM practice_plans').fetchone()[0]==1


def test_legacy_errors_backfill_once_and_survive_restart(setup):
    from backend.moirae.store import Store
    app,c,uid=setup;qid=answer(c)
    with app.state.store.connect(write=True) as db:
        db.execute('DELETE FROM review_schedule');db.execute('DELETE FROM schema_version WHERE version=8')
    reopened=Store(app.state.store.path)
    with reopened.connect() as db:before=dict(db.execute('SELECT * FROM review_schedule').fetchone())
    assert before['question_id']==qid
    Store(app.state.store.path)
    with reopened.connect() as db:assert dict(db.execute('SELECT * FROM review_schedule').fetchone())==before


def test_full_error_review_success_cycle(setup):
    app,c,uid=setup
    session=c.post('/api/planner/start',json={'minutes':15}).json();first=session['question']['id']
    while session['question']:
        q=session['question'];choice=BY_ID[q['id']].answer
        if q['id']==first:choice=next(x for x in 'abcde' if x!=choice)
        response=c.post('/api/practice/answer',json=dict(session_id=session['id'],question_id=q['id'],choice=choice,key=str(uuid.uuid4())))
        assert response.status_code==200;session=response.json()['session']
    with app.state.store.connect(write=True) as db:
        db.execute('UPDATE review_schedule SET due_at=? WHERE user_id=? AND question_id=?',(int(time.time())-1,uid,first))
    session=c.post('/api/planner/start',json={'minutes':15}).json()
    assert session['question']['id']==first
    result=c.post('/api/practice/answer',json=dict(session_id=session['id'],question_id=first,choice=BY_ID[first].answer,key=str(uuid.uuid4()))).json()
    assert result['correct'] and result['review_schedule']['stage']==1
    assert result['review_schedule']['due_at']>=int(time.time())+3*DAY-2


def test_all_future_reviews_do_not_create_empty_session(setup):
    app,c,uid=setup;now=int(time.time())
    with app.state.store.connect(write=True) as db:
        db.executemany('INSERT INTO review_schedule VALUES(?,?,0,?,?)',[(uid,q.id,now+DAY,now) for q in QUESTIONS])
    assert c.get('/api/planner').json()['question_count']==0
    assert c.post('/api/planner/start',json={'minutes':15}).status_code==409
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM practice_sessions').fetchone()[0]==0
