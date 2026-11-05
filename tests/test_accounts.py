import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
import pytest
from fastapi.testclient import TestClient
from backend.moirae.app import create_app
from backend.moirae.accounts import POLICY_VERSION
from backend.moirae.security import digest

BASE='http://localhost:8000';PASSWORD='senha-exclusiva-123'

@pytest.fixture
def setup(tmp_path):
    app=create_app(str(tmp_path/'db.sqlite3'),origin=BASE,secure=False)
    c=TestClient(app,base_url=BASE,headers={'Origin':BASE})
    return app,c


def register(app,c,email='account@example.test'):
    r=c.post('/api/auth/register',json={'email':email,'password':PASSWORD,'accept_terms':True,'adult_pilot':True})
    assert r.status_code==201,r.text
    c.headers['X-CSRF-Token']=r.json()['csrf'];return app.state.mailer.messages[-1]['link'].split('#token=')[1]


def verify(c,token):return c.post('/api/auth/verify-email',json={'token':token})


def reset_token(app,c,email='account@example.test'):
    r=c.post('/api/auth/request-reset',json={'email':email});assert r.status_code==200
    return app.state.mailer.messages[-1]['link'].split('#token=')[1]


def test_unverified_cannot_study_until_single_use_confirmation(setup):
    app,c=setup;token=register(app,c)
    assert c.get('/api/auth/me').json()['email_verified'] is False
    assert c.get('/api/practice/current').status_code==403
    assert c.get('/api/exams/current').status_code==403
    assert verify(c,token).status_code==200
    assert verify(c,token).status_code==400
    assert c.get('/api/practice/current').status_code==200
    with app.state.store.connect() as db:
        row=db.execute('SELECT * FROM user_profiles').fetchone()
        assert row['policy_version']==POLICY_VERSION and row['adult_pilot']==1


def test_tokens_are_hashed_and_not_returned_in_api(setup):
    app,c=setup;token=register(app,c)
    with app.state.store.connect() as db:
        row=db.execute('SELECT * FROM account_tokens').fetchone()
        assert row['token_hash']==digest(token) and token not in str(dict(row))
    assert token not in c.get('/api/auth/me').text
    path=list(app.state.mailer.directory.iterdir())[0]
    if os.name != "nt":  # Windows uses ACLs, not POSIX permission bits.
        assert path.stat().st_mode & 0o777 == 0o600
    assert urlparse(app.state.mailer.messages[-1]['link']).query==''


def test_expiry_and_resend_invalidates_previous_link(setup):
    app,c=setup;old=register(app,c)
    assert c.post('/api/account/resend-verification',json={}).status_code==200
    new=app.state.mailer.messages[-1]['link'].split('#token=')[1]
    assert verify(c,old).status_code==400
    app.state.accounts.clock=lambda:10**12
    assert verify(c,new).status_code==400


def test_password_reset_revokes_sessions_and_is_single_use(setup):
    app,c=setup;verify(c,register(app,c));cookie=dict(c.cookies);token=reset_token(app,c)
    new='senha-nova-exclusiva-456'
    r=c.post('/api/auth/reset-password',json={'token':token,'password':new});assert r.status_code==200
    assert c.get('/api/auth/me').status_code==401
    assert c.post('/api/auth/reset-password',json={'token':token,'password':new}).status_code==400
    assert c.post('/api/auth/login',json={'email':'account@example.test','password':PASSWORD}).status_code==401
    assert c.post('/api/auth/login',json={'email':'account@example.test','password':new}).status_code==200
    old=TestClient(app,base_url=BASE,cookies=cookie);assert old.get('/api/auth/me').status_code==401


def test_generic_password_reset_response(setup):
    app,c=setup;register(app,c)
    known=c.post('/api/auth/request-reset',json={'email':'account@example.test'})
    unknown=c.post('/api/auth/request-reset',json={'email':'absent@example.test'})
    assert known.status_code==unknown.status_code==200 and known.json()==unknown.json()


def test_export_scoped_and_no_security_secrets(setup):
    app,c=setup;verify(c,register(app,c))
    b=TestClient(app,base_url=BASE,headers={'Origin':BASE});verify(b,register(app,b,'another@example.test'))
    e=c.post('/api/exams/start',json={'day':1,'key':'00000000-0000-4000-8000-000000000001'}).json()
    assert c.post('/api/exams/'+e['id']+'/essay',json={'text':'Minha redação autoral.','revision':0}).status_code==200
    assert c.post('/api/account/export',json={'password':'senha-errada-123'}).status_code==403
    r=c.post('/api/account/export',json={'password':PASSWORD});assert r.status_code==200
    assert 'attachment' in r.headers['content-disposition']
    data=r.json();assert data['account']['email']=='account@example.test'
    assert data['exams'][0]['essay']=='Minha redação autoral.'
    assert 'another@example.test' not in r.text
    for forbidden in ('password_hash','token_hash','csrf','start_key'):assert forbidden not in r.text


def test_delete_reauth_csrf_and_all_owned_records(setup):
    app,c=setup;verify(c,register(app,c));cookie=dict(c.cookies)
    c.post('/api/practice/start',json={})
    c.post('/api/exams/start',json={'day':1,'key':'00000000-0000-4000-8000-000000000001'})
    assert c.post('/api/account/delete',json={'password':PASSWORD,'confirmation':'NO'}).status_code==422
    assert c.post('/api/account/delete',json={'password':'senha-errada-123','confirmation':'EXCLUIR'}).status_code==403
    assert c.post('/api/account/delete',json={'password':PASSWORD,'confirmation':'EXCLUIR'},headers={'X-CSRF-Token':'bad'}).status_code==403
    assert c.post('/api/account/delete',json={'password':PASSWORD,'confirmation':'EXCLUIR'}).status_code==200
    with app.state.store.connect() as db:
        for table in ('users','user_profiles','auth_sessions','account_tokens','mock_exams','mock_items','practice_sessions','session_questions','attempts','idempotency'):
            assert db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0
    assert not list(app.state.mailer.directory.iterdir())
    assert TestClient(app,base_url=BASE,cookies=cookie).get('/api/auth/me').status_code==401


def test_registration_requires_terms_and_adult_and_blocks_unconfigured_public_delivery(tmp_path):
    app=create_app(str(tmp_path/'db'),origin='https://pilot.example.test',secure=True)
    c=TestClient(app,base_url='https://pilot.example.test',headers={'Origin':'https://pilot.example.test'})
    assert c.post('/api/auth/register',json={'email':'a@example.test','password':PASSWORD}).status_code==422
    assert c.post('/api/auth/register',json={'email':'a@example.test','password':PASSWORD,'accept_terms':True,'adult_pilot':False}).status_code==422
    assert c.post('/api/auth/register',json={'email':'a@example.test','password':PASSWORD,'accept_terms':True,'adult_pilot':True}).status_code==503
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM users').fetchone()[0]==0


def test_concurrent_confirmation_only_one_succeeds(setup):
    app,c=setup;token=register(app,c)
    def send(_):
        with TestClient(app,base_url=BASE,headers={'Origin':BASE}) as other:return verify(other,token).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(send,range(2)))==[200,400]


def test_deleting_one_account_preserves_other_user(setup):
    app,a=setup;verify(a,register(app,a))
    b=TestClient(app,base_url=BASE,headers={'Origin':BASE});verify(b,register(app,b,'kept@example.test'))
    assert a.post('/api/account/delete',json={'password':PASSWORD,'confirmation':'EXCLUIR'}).status_code==200
    assert b.get('/api/auth/me').json()['email']=='kept@example.test'
    assert b.get('/api/practice/current').status_code==200
    with app.state.store.connect() as db:assert db.execute('SELECT count(*) FROM users').fetchone()[0]==1


def test_no_token_or_outbox_endpoint_and_export_requires_csrf(setup):
    app,c=setup;register(app,c)
    assert c.post('/api/account/export',json={'password':PASSWORD},headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert c.get('/var/mail-outbox').status_code==404
    assert c.get('/api/account/tokens').status_code==404
