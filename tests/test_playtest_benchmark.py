import pytest
from backend.moirae.local_playtest import create_playtest
from backend.moirae.essay_benchmark import compare
from backend.moirae.store import Store
from backend.moirae.security import verify

def test_playtest_is_isolated_and_never_overwrites(tmp_path):
    path=tmp_path/'test.sqlite3';result=create_playtest(path,'tester@example.test','test-password-123')
    with Store(result['database']).connect() as db:
        user=db.execute('SELECT * FROM users').fetchone();assert verify(user['password_hash'],'test-password-123')
        assert db.execute('SELECT email_verified FROM user_profiles').fetchone()[0]==1
        assert db.execute('SELECT essay_credits FROM access_grants').fetchone()[0]==30
        assert db.execute('SELECT status FROM billing_orders').fetchone()[0]=='local_test'
    before=path.read_bytes()
    with pytest.raises(FileExistsError):create_playtest(path,'other@example.test','test-password-123')
    assert path.read_bytes()==before

def test_benchmark_metrics_and_version_separation():
    row=dict(id='synthetic-only',human_reviewed=True,authorized_use=True,model='test-model',rubric_version='test',prompt_version='test',human_scores={c:120 for c in '12345'},predicted_scores={c:160 for c in '12345'})
    report=compare([row,{**row,'id':'other','model':'test-model-2'}])
    assert not report['approved'] and len(report['groups'])==2
    assert report['groups'][0]['competencies']['1']==dict(mean_absolute_error=40.0,exact_agreement=0.0,within_40=1.0)
    for invalid in ([],[row,row],[{**row,'human_reviewed':False}],[{**row,'human_scores':{'1':True}}]):
        with pytest.raises(ValueError):compare(invalid)


def test_seeded_account_can_login_and_open_paid_tools(tmp_path):
    from fastapi.testclient import TestClient
    from backend.moirae.app import create_app
    path=tmp_path/'account.sqlite3';create_playtest(path,'tester@example.test','test-password-123')
    app=create_app(str(path),origin='http://localhost:8000',secure=False)
    client=TestClient(app,base_url='http://localhost:8000',headers={'Origin':'http://localhost:8000'})
    response=client.post('/api/auth/login',json={'email':'tester@example.test','password':'test-password-123'})
    assert response.status_code==200
    assert client.get('/api/review').status_code==200
    assert client.get('/api/planner').status_code==200
    assert client.get('/api/essay-evaluations').status_code==503
