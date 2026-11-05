"""Registration gates apply to Free and paid accounts, including direct files."""
import pytest
from fastapi.testclient import TestClient
from test_mvp import env, register
from test_review import grant


@pytest.mark.parametrize('path',[
    '/api/learning-library','/api/enem-archive','/acervo-enem/2025/example.pdf',
])
def test_anonymous_content_requests_require_login(env,path):
    _,c=env
    assert c.get(path).status_code==401


@pytest.mark.parametrize('path',[
    '/learning-library.json','/assets/learning-library.json','/data/learning-library.json',
    '/essay-fixture.js','/assets/essay-fixture.js',
])
def test_old_public_content_files_are_not_served(env,path):
    _,c=env
    assert c.get(path).status_code==404


def test_landing_page_contains_registration_cta_without_questions(env):
    _,c=env;html=c.get('/').text
    for old in ('id="question-form"','id="rewrite-form"','Uma mochila custa R$ 200','R$ 170','essay-fixture.js'):
        assert old not in html
    assert 'Cadastro gratuito' in html and '/estudar' in html


@pytest.mark.parametrize('paid',[False,True])
def test_verified_free_and_paid_accounts_can_access_content(env,paid):
    app,c=env;register(c)
    if paid:
        with app.state.store.connect() as db:uid=db.execute('SELECT id FROM users').fetchone()[0]
        grant(app,uid)
    assert c.get('/api/auth/me').json()['plan']==('essencial' if paid else 'free')
    library=c.get('/api/learning-library')
    assert library.status_code==200 and library.headers['cache-control']=='no-store'
    assert len(library.json()['tracks'])==6
    assert sum(len(t['lessons']) for t in library.json()['tracks'])==18
    assert c.get('/api/enem-archive').status_code==200
    assert c.post('/api/practice/start',json={}).status_code==200
    assert c.get('/api/practice/current').json()['quota']['used']==0


def test_unverified_account_does_not_bypass_existing_student_controls(env):
    _,c=env
    result=c.post('/api/auth/register',json=dict(email='unverified@example.test',password='senha-exclusiva-123',accept_terms=True,adult_pilot=True))
    assert result.status_code==201
    for path in ('/api/learning-library','/api/enem-archive','/acervo-enem/2025/example.pdf'):
        assert c.get(path).status_code==403


def test_logout_revokes_content_access_even_with_previous_session_cookie(env):
    app,c=env;register(c)
    assert c.get('/api/learning-library').status_code==200
    old=dict(c.cookies)
    assert c.post('/api/auth/logout',json={}).status_code==200
    stale=TestClient(app,base_url='http://localhost:8000',cookies=old)
    for client in (c,stale):
        assert client.get('/api/learning-library').status_code==401
        assert client.get('/api/enem-archive').status_code==401


def test_library_local_progress_namespace_is_account_specific(env):
    app,c=env;register(c)
    first=c.get('/api/learning-library').json()['progress_key']
    assert c.get('/api/learning-library').json()['progress_key']==first
    other=TestClient(app,base_url='http://localhost:8000',headers={'Origin':'http://localhost:8000'})
    register(other,'other-library@example.test')
    second=other.get('/api/learning-library').json()['progress_key']
    assert first!=second and 'aluno@example.test' not in first and 'other-library@example.test' not in second
