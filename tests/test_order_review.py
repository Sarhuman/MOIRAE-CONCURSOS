"""Read-only operational triage on synthetic financial scenarios."""
import json
import sqlite3
import uuid
import pytest
from backend.moirae.order_review import inspect, readonly, main, ReviewUnavailable
from test_sandbox_orders import env, start, pay, contract


def dump(store):
    with store.connect() as db:return list(db.iterdump())


def test_review_uncertain_response_is_read_only_and_redacts_sensitive_fields(env):
    app,fake,clock=env
    def uncertain(*args):raise TimeoutError('do not print this provider exception')
    fake.preference=uncertain
    with pytest.raises(TimeoutError):start(env)
    with app.state.store.connect(write=True) as db:
        db.execute("UPDATE billing_orders SET checkout_url='https://example.test/?secret=PRIVATE-URL',payment_id='PRIVATE-PAYMENT'")
    before=dump(app.state.store)
    report=inspect(app.state.store.path,now=clock[0])
    assert dump(app.state.store)==before
    assert report['read_only'] and report['total_matching']==1
    item=report['items'][0]
    assert item['reason']=='provider_response_uncertain' and item['payment_linked']
    assert item['automatic_resolution_available'] is False
    assert item['lot'] is None
    text=json.dumps(report)
    for secret in ('PRIVATE-URL','PRIVATE-PAYMENT','alice@example.test','coupon_code','checkout_url','user_id','do not print'):
        assert secret not in text


def test_late_payment_review_and_normal_orders_are_distinguished(env):
    app,_,clock=env
    first=start(env)['order_id'];pay(env,first)
    other=start(env,uid='bob')['order_id'];clock[0]+=1801;pay(env,other,pid='101')
    report=inspect(app.state.store.path,now=clock[0])
    assert report['total_matching']==1
    assert report['items'][0]['order_id']==other
    assert report['items'][0]['reason']=='payment_after_reservation_closed'
    assert report['items'][0]['lot'] is None
    selected=inspect(app.state.store.path,order_id=first,now=clock[0])
    assert selected['items'][0]['contract_state']=='fulfilled'
    assert selected['items'][0]['lot']['units']==5
    assert selected['items'][0]['requires_review'] is False
    assert selected['items'][0]['reason']=='not_flagged'


def test_refund_consumption_exposes_counts_without_resolving(env):
    app,_,clock=env
    oid=start(env)['order_id'];pay(env,oid)
    reservation=app.state.wallet.reserve('alice','essay')
    app.state.wallet.settle('alice',reservation['id'],'consume')
    clock[0]+=1;pay(env,oid,status='refunded')
    before=dump(app.state.store)
    report=inspect(app.state.store.path,now=clock[0])
    item=report['items'][0]
    assert item['reason']=='refund_requires_monetary_policy'
    assert item['lot']['consumed']==1 and item['lot']['revoked']
    assert item['action']=='manual_review_only'
    assert dump(app.state.store)==before


def test_unknown_reason_and_corrupt_snapshot_do_not_leak_text(env):
    app,_,clock=env
    oid=start(env)['order_id']
    with app.state.store.connect(write=True) as db:
        db.execute("UPDATE sandbox_order_contracts SET state='needs_review',review_reason=?,snapshot=? WHERE order_id=?",('PRIVATE-TOKEN customer@example.test','PRIVATE-JSON',oid))
        db.execute("UPDATE billing_orders SET status='needs_review' WHERE id=?",(oid,))
    report=inspect(app.state.store.path,now=clock[0]);item=report['items'][0]
    assert item['reason']=='unclassified_review'
    assert 'invalid_contract_snapshot' in item['anomalies']
    assert 'PRIVATE' not in json.dumps(report) and 'customer@example.test' not in json.dumps(report)


def test_refund_request_and_pagination_are_honest(env):
    app,_,clock=env
    first=start(env)['order_id'];second=start(env,uid='bob')['order_id']
    app.state.billing.request_refund('alice',first)
    app.state.billing.request_refund('bob',second)
    report=inspect(app.state.store.path,limit=1,now=clock[0])
    assert report['total_matching']==2 and report['returned']==1 and report['has_more']
    assert report['items'][0]['reason']=='refund_request_recorded'


def test_missing_database_uuid_and_legacy_schema_never_create_or_migrate(tmp_path):
    path=tmp_path/'absent.sqlite3'
    with pytest.raises(FileNotFoundError):inspect(path)
    assert not path.exists()
    with pytest.raises(ReviewUnavailable):inspect(path,order_id='not-a-uuid')
    db=sqlite3.connect(path);db.execute('CREATE TABLE schema_version(version INTEGER PRIMARY KEY)');db.execute('INSERT INTO schema_version VALUES(1)');db.commit();db.close()
    before=path.read_bytes()
    with pytest.raises(ReviewUnavailable):inspect(path)
    assert path.read_bytes()==before


def test_readonly_connection_rejects_writes_and_cli_handles_unknown_order(env,capsys):
    app,_,clock=env
    with readonly(app.state.store.path) as db:
        with pytest.raises(sqlite3.OperationalError):db.execute("UPDATE billing_orders SET status='approved'")
    with pytest.raises(SystemExit) as exc:main(['--database',app.state.store.path,'--order',str(uuid.uuid4())])
    assert exc.value.code==1
    assert 'Pedido não encontrado' in capsys.readouterr().err


def test_cli_reports_only_its_snapshot_without_external_provider(env,capsys):
    app,fake,_=env
    oid=start(env)['order_id']
    fake.payment=lambda *args:pytest.fail('No provider call is allowed')
    main(['--database',app.state.store.path,'--order',oid])
    report=json.loads(capsys.readouterr().out)
    assert report['read_only'] and report['returned']==1


def test_mismatched_lot_ownership_is_reported_without_other_account_counts(env):
    app,_,clock=env
    alice=start(env)['order_id'];pay(env,alice)
    bob=start(env,uid='bob')['order_id'];pay(env,bob,pid='101')
    with app.state.store.connect(write=True) as db:
        db.execute("UPDATE sandbox_credit_lots SET user_id='bob' WHERE id=?",(contract(env,alice)['lot_id'],))
        db.execute("UPDATE billing_orders SET status='needs_review' WHERE id=?",(alice,))
    before=dump(app.state.store)
    item=inspect(app.state.store.path,order_id=alice,now=clock[0])['items'][0]
    assert 'lot_owner_mismatch' in item['anomalies'] and item['lot'] is None
    assert item['requires_review']
    assert dump(app.state.store)==before


def test_windows_friendly_paths_with_spaces_and_unicode(tmp_path):
    from backend.moirae.store import Store
    folder=tmp_path/'Pasta com espaços';folder.mkdir()
    store=Store(str(folder/'banco #1.sqlite3'))
    report=inspect(store.path)
    assert report['total_matching']==0 and report['items']==[]
