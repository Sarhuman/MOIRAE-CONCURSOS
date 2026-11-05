import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import pytest
from fastapi import HTTPException
from backend.moirae.store import Store
from backend.moirae.sandbox_coupons import SandboxCoupons

ZONE=ZoneInfo('America/Sao_Paulo')
def stamp(year,month,day):return int(datetime(year,month,day,10,30,tzinfo=ZONE).timestamp())

@pytest.mark.parametrize('start,end',[
    ((2026,11,4),(2027,2,4)),
    ((2026,1,31),(2026,4,30)),
    ((2027,11,30),(2028,2,29)),
    ((2026,11,30),(2027,2,28)),
])
def test_three_calendar_months_preserve_time_and_clamp_end_of_month(start,end):
    assert SandboxCoupons.calendar_expiry(stamp(*start),3)==stamp(*end)


def test_approved_probability_space_and_losing_draws_are_not_coupons(tmp_path,monkeypatch):
    store=Store(str(tmp_path/'policy.sqlite3'));now=stamp(2026,11,4)
    service=SandboxCoupons(store,True,lambda:now)
    service.configure_approved('approved-v1',now-1,now+60,100)
    rules=service.rules('approved-v1')
    assert rules['valid_months']==3 and rules['valid_seconds'] is None
    assert rules['products']==['avancado']
    assert rules['outcomes']==[dict(discount_bps=500,weight=1,total_weight=100),dict(discount_bps=0,weight=99,total_weight=100)]
    with store.connect(write=True) as db:
        for n in range(100):db.execute('INSERT INTO users VALUES(?,?,?,?)',(str(n),f'{n}@example.test','unused',now))
    tickets=iter(range(100))
    def ticket(limit):
        assert limit==100
        return next(tickets)
    monkeypatch.setattr('backend.moirae.sandbox_coupons.secrets.randbelow',ticket)
    draws=[service.draw(str(n),'approved-v1') for n in range(100)]
    assert sum(d['won'] for d in draws)==1 # Exhaustive ticket-space test, not a claim about random runs.
    winner=draws[0]
    assert winner['expires_at']==stamp(2027,2,4)
    assert winner['discount_bps']==500 and winner['code']
    assert all(d['code'] is None and d['discount_bps']==0 for d in draws[1:])
    assert service.draw('1','approved-v1')==draws[1]
    with store.connect() as db:
        losing_code=db.execute("SELECT code FROM sandbox_coupons WHERE user_id='1'").fetchone()[0]
    with pytest.raises(HTTPException) as exc:service.quote('1',losing_code,'avancado')
    assert exc.value.status_code==409


def test_avancado_only_full_validity_after_issuance_ends_and_exact_expiry(tmp_path,monkeypatch):
    store=Store(str(tmp_path/'expiry.sqlite3'));now=[stamp(2026,11,4)]
    with store.connect(write=True) as db:db.execute("INSERT INTO users VALUES('u','u@example.test','unused',1)")
    service=SandboxCoupons(store,True,lambda:now[0])
    service.configure_approved('approved-v1',now[0]-1,now[0]+60,10)
    monkeypatch.setattr('backend.moirae.sandbox_coupons.secrets.randbelow',lambda _:0)
    draw=service.draw('u','approved-v1')
    now[0]+=3600 # The issuance window ended; the issued coupon is still valid.
    quote=service.quote('u',draw['code'],'avancado')
    assert (quote['amount_cents'],quote['discount_cents'],quote['total_cents'])==(11000,550,10450)
    with pytest.raises(HTTPException):service.quote('u',draw['code'],'essencial')
    now[0]=draw['expires_at']
    with pytest.raises(HTTPException) as exc:service.quote('u',draw['code'],'avancado')
    assert exc.value.status_code==409


def test_policy_migration_preserves_legacy_validity(tmp_path):
    store=Store(str(tmp_path/'legacy.sqlite3'))
    service=SandboxCoupons(store,True,lambda:1000)
    service.configure('seconds',900,3000,500,['essencial'],[dict(discount_bps=1000,weight=1)],10)
    with store.connect(write=True) as db:
        db.execute('ALTER TABLE sandbox_coupon_campaigns DROP COLUMN valid_months')
        db.execute('DELETE FROM schema_version WHERE version=14')
    fresh=Store(store.path);Store(store.path)
    assert SandboxCoupons(fresh,True,lambda:1000).rules('seconds')['valid_seconds']==500
    assert SandboxCoupons(fresh,True,lambda:1000).rules('seconds')['valid_months']==0
