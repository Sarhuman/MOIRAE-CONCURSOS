import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.moirae.commercial import catalog,quote
from backend.moirae.app import create_app

@pytest.mark.parametrize('product,cycles,total',[('essencial',1,4400),('avancado',1,11000),('essencial',6,23760),('essencial',12,44880),('avancado',6,59400),('avancado',12,112200),('creditos-5',1,2750),('creditos-10',1,4950),('creditos-30',1,13200)])
def test_markup_once_and_no_buyer_interest_in_single_payment(product,cycles,total):
    q=quote(product,cycles,1)
    assert q['product_total_cents']==total and q['buyer_total_cents']==total
    assert q['estimated_financing_cents']==0 and q['checkout_enabled'] is False


def test_installment_estimate_never_becomes_confirmed_quote():
    q=quote('essencial',12,12)
    assert q['product_total_cents']==44880 and q['reference_installment_basis_points']==1728
    assert q['estimated_financing_cents']==7756 and q['estimated_buyer_total_cents']==52636
    assert sum(q['estimated_installments_cents'])==52636 and len(q['estimated_installments_cents'])==12
    assert q['buyer_total_cents'] is None and q['installment_cents'] is None and q['provider_quote_required']
    assert q['credits']==10 and q['access_days']==360 # Not 120 credits upfront.


@pytest.mark.parametrize('args',[('fake',1,1),('essencial',2,1),('essencial',1,2),('creditos-5',6,1),('creditos-30',1,4),('essencial',True,1)])
def test_invalid_product_duration_or_installments_rejected(args):
    with pytest.raises(HTTPException):quote(*args)


def test_public_simulation_is_read_only_and_cannot_checkout(tmp_path):
    app=create_app(str(tmp_path/'db'),origin='http://localhost:8000',secure=False);c=TestClient(app,base_url='http://localhost:8000')
    assert c.get('/api/commercial/quote?product=avancado&cycles=12&installments=12').status_code==200
    assert c.get('/api/commercial/catalog').json()['checkout_enabled'] is False
    assert c.get('/api/commercial/quote?product=essencial&cycles=2').status_code==422
    with app.state.store.connect() as db:
        assert db.execute('SELECT count(*) FROM billing_orders').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM access_grants').fetchone()[0]==0


def test_library_has_complete_authored_exercises_separate_from_practice_catalog():
    from backend.moirae.catalog import BY_ID
    data=json.loads(Path('data/learning-library.json').read_text(encoding='utf-8'));ids=[]
    assert len(data['tracks'])==6
    for track in data['tracks']:
        assert track['status']=='pilot_editorial_review' and len(track['lessons'])==3
        for lesson in track['lessons']:
            ids.append(lesson['id']);assert lesson['id'] not in BY_ID
            assert len(lesson['options'])==4 and type(lesson['answer']) is int and 0<=lesson['answer']<4
            assert all(lesson[k] for k in ('concept','example','explanation','question'))
    assert len(ids)==len(set(ids))==18
