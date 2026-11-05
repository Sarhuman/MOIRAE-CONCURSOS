"""Read-only local triage. Never contacts providers, migrates or settles orders."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid


class ReviewUnavailable(ValueError):
    pass


REASONS = {
    'Resposta do provedor incerta; conferir referência antes de retentar.': 'provider_response_uncertain',
    'Pagamento confirmado após encerramento da reserva técnica.': 'payment_after_reservation_closed',
    'Outro acesso já ativo na confirmação; não acumular períodos automaticamente.': 'active_access_conflict',
    'Reembolso com consumo ou valor parcial: decisão monetária manual pendente.': 'refund_requires_monetary_policy',
    'Estado do provedor regrediu após concessão.': 'provider_state_regression',
    'Reserva de cupom indisponível na confirmação do pagamento.': 'coupon_confirmation_conflict',
}
EVIDENCE = {
    'provider_response_uncertain': ['Conferir preferência/pagamento pela referência do pedido no ambiente sandbox.', 'Distinguir ausência de pagamento de resposta perdida antes de qualquer nova tentativa.'],
    'payment_after_reservation_closed': ['Conferir horário e situação do pagamento verificado e o encerramento da reserva local.', 'Não reaproveitar uma reserva de cupom liberada ou usada em outro pedido.'],
    'active_access_conflict': ['Conferir os períodos de acesso existentes e o contrato original.', 'Aguardar regra de acumulação, remarcação ou devolução; não estender acesso automaticamente.'],
    'refund_requires_monetary_policy': ['Conferir valores pagos/devolvidos no provedor e créditos já consumidos.', 'Aguardar decisão monetária aprovada; não calcular reembolso proporcional automaticamente.'],
    'provider_state_regression': ['Conferir a versão e o estado atual do pagamento no provedor.', 'Investigar a divergência mantendo o bloqueio existente.'],
    'coupon_confirmation_conflict': ['Conferir titularidade, validade, campanha e histórico da reserva de cupom.', 'Não recriar cupom, resgate ou capacidade para forçar confirmação.'],
    'refund_request_recorded': ['Conferir a solicitação e o pagamento no provedor.', 'Solicitação registrada não é estorno concluído nem autorização para devolver dinheiro.'],
    'not_flagged': ['Pedido sem sinalização operacional de análise ou solicitação de reembolso nesta consulta.', 'Esta consulta local não substitui a conferência do pagamento no provedor.'],
    'unclassified_review': ['Examinar o pedido localmente com acesso operacional autorizado.', 'Não tratar motivo ausente/desconhecido como autorização de concessão.'],
}
STATUSES = {'preparing','pending','in_process','authorized','approved','failed','expired','cancelled','rejected','refunded','charged_back','revoked','needs_review','local_test'}
PRODUCTS = {'essencial','avancado','creditos-5','creditos-10','creditos-30'}
CONTRACT_STATES = {'pending','fulfilled','expired','cancelled','revoked','needs_review'}
CASE_FILTER = "(b.status='needs_review' OR c.state='needs_review' OR b.refund_requested_at IS NOT NULL)"


@contextmanager
def readonly(database):
    target=Path(database).resolve(strict=True)
    if not target.is_file():raise ReviewUnavailable('Banco inacessível ou incompatível.')
    db=sqlite3.connect(target.as_uri()+'?mode=ro',uri=True,timeout=5,isolation_level=None)
    db.row_factory=sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        if not db.execute('SELECT 1 FROM schema_version WHERE version=15').fetchone():
            raise ReviewUnavailable('Diagnóstico exige banco com schema 15; nenhuma migração foi executada.')
        yield db
    finally:
        db.close()


def number(value):
    return value if type(value) is int and value>=0 else None


def case(db, row, now):
    anomalies=[]
    reason=REASONS.get(row['review_reason'],'unclassified_review')
    if reason=='unclassified_review' and row['refund_requested_at'] is not None:
        reason='refund_request_recorded'
    has_contract=row['contract_state'] is not None
    trusted_contract=has_contract and row['contract_user_id']==row['user_id']
    if has_contract and not trusted_contract:anomalies.append('contract_owner_mismatch')
    raw={}
    if trusted_contract:
        try:
            raw=json.loads(row['snapshot'])
            if not isinstance(raw,dict):raw={};anomalies.append('invalid_contract_snapshot')
        except (ValueError,TypeError):anomalies.append('invalid_contract_snapshot')
    amounts={key:number(raw.get(key)) for key in ('amount_cents','discount_cents','total_cents','credits','validity_days')}
    if trusted_contract:
        required=('amount_cents','discount_cents','total_cents')
        invalid_numbers=any(amounts[k] is None for k in required)
        if row['contract_kind']=='credit_pack':
            invalid_numbers=invalid_numbers or any(amounts[k] is None or amounts[k]<=0 for k in ('credits','validity_days'))
        if invalid_numbers:anomalies.append('invalid_contract_numbers')
        if raw.get('currency')!='BRL':anomalies.append('invalid_contract_currency')
        if amounts['total_cents']!=number(row['amount_cents']):anomalies.append('contract_order_amount_mismatch')
        if all(amounts[k] is not None for k in ('amount_cents','discount_cents','total_cents')) and amounts['amount_cents']-amounts['discount_cents']!=amounts['total_cents']:
            anomalies.append('invalid_contract_arithmetic')
        if row['contract_kind']=='credit_pack' and row['contract_state']=='fulfilled' and not row['lot_id']:
            anomalies.append('missing_fulfillment_lot')
    lot=None
    if trusted_contract and row['lot_id']:
        record=db.execute('SELECT user_id,available,reserved,consumed,units,expires_at,revoked_at FROM sandbox_credit_lots WHERE id=?',(row['lot_id'],)).fetchone()
        if record is None:anomalies.append('missing_lot')
        elif record['user_id']!=row['user_id']:anomalies.append('lot_owner_mismatch')
        else:
            lot={k:number(record[k]) for k in ('available','reserved','consumed','units','expires_at')}
            lot['revoked']=record['revoked_at'] is not None
            lot['expired']=lot['expires_at'] is None or lot['expires_at']<=now
            counts=db.execute("SELECT coalesce(sum(status='reserved'),0) AS reserved,coalesce(sum(status='consumed'),0) AS consumed FROM sandbox_credit_reservations WHERE lot_id=? AND user_id=?",(row['lot_id'],row['user_id'])).fetchone()
            if lot['reserved']!=counts['reserved']:anomalies.append('reservation_balance_mismatch')
            if lot['consumed']!=counts['consumed']:anomalies.append('consumption_balance_mismatch')
            if (row['status']=='needs_review' or row['contract_state']=='needs_review') and not lot['revoked'] and not lot['expired'] and (lot['available'] or 0)>0:
                anomalies.append('review_lot_still_spendable')
    hold=db.execute('SELECT user_id,status,expires_at FROM sandbox_coupon_holds WHERE order_id=?',(row['id'],)).fetchone()
    coupon=None
    if hold:
        if hold['user_id']!=row['user_id']:anomalies.append('coupon_hold_owner_mismatch')
        else:
            coupon=dict(state=hold['status'] if hold['status'] in ('reserved','released','redeemed') else 'unknown',expired=hold['expires_at']<=now)
            if (row['status']=='needs_review' or row['contract_state']=='needs_review') and hold['status']=='reserved' and hold['expires_at']>now:
                anomalies.append('review_coupon_still_reserved')
    flagged=row['status']=='needs_review' or row['contract_state']=='needs_review' or row['refund_requested_at'] is not None
    requires_review=flagged or bool(anomalies)
    if not requires_review:reason='not_flagged'
    try:order_id=str(uuid.UUID(row['id']))
    except (ValueError,TypeError,AttributeError):
        order_id=None;anomalies.append('invalid_order_identifier');requires_review=True;reason='unclassified_review'
    # Do not emit free text, customer IDs, payment IDs, URLs, coupon codes or raw JSON.
    return dict(order_id=order_id,product=row['plan_id'] if row['plan_id'] in PRODUCTS else 'unknown',
        status=row['status'] if row['status'] in STATUSES else 'unknown',
        contract_state=row['contract_state'] if row['contract_state'] in CONTRACT_STATES else None,
        reason=reason,refund_requested=row['refund_requested_at'] is not None,
        payment_linked=bool(row['payment_id']),amount_cents=number(row['amount_cents']),contract=amounts if trusted_contract else None,
        lot=lot,coupon_hold=coupon,anomalies=anomalies,required_evidence=EVIDENCE[reason],
        requires_review=requires_review,action='manual_review_only' if requires_review else 'inspection_only',automatic_resolution_available=False)


def inspect(database, order_id=None, limit=100, now=None):
    if type(limit) is not int or not 1<=limit<=1000:raise ReviewUnavailable('Limite deve estar entre 1 e 1000.')
    if order_id is not None:
        try:order_id=str(uuid.UUID(str(order_id)))
        except (ValueError,TypeError,AttributeError):raise ReviewUnavailable('Identificador de pedido inválido.') from None
    now=int(time.time()) if now is None else int(now)
    with readonly(database) as db:
        where='b.id=?' if order_id else CASE_FILTER
        args=(order_id,) if order_id else ()
        join='FROM billing_orders b LEFT JOIN sandbox_order_contracts c ON c.order_id=b.id'
        total=db.execute('SELECT count(*) '+join+' WHERE '+where,args).fetchone()[0]
        if order_id and not total:raise ReviewUnavailable('Pedido não encontrado.')
        rows=db.execute('SELECT b.id,b.user_id,b.plan_id,b.amount_cents,b.status,b.payment_id,b.refund_requested_at,c.state AS contract_state,c.user_id AS contract_user_id,c.kind AS contract_kind,c.snapshot,c.lot_id,c.review_reason '+join+' WHERE '+where+' ORDER BY b.created_at,b.id LIMIT ?',args+(limit,)).fetchall()
        items=[case(db,row,now) for row in rows]
    return dict(read_only=True,sandbox_pilot=True,snapshot_at=now,total_matching=total,returned=len(items),has_more=total>len(items),items=items,
        notice='Triagem local sem consulta ao provedor, migração, concessão, resolução ou estorno. Não comprova homologação externa. IDs de pedidos e valores são dados operacionais; não publique o relatório.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True)
    parser.add_argument('--order',dest='order_id')
    parser.add_argument('--limit',type=int,default=100)
    args=parser.parse_args(argv)
    try:
        result=inspect(args.database,args.order_id,args.limit)
    except ReviewUnavailable as exc:
        parser.exit(1,str(exc)+'\n')
    except (OSError,sqlite3.Error,ValueError,TypeError):
        parser.exit(1,'Banco inacessível ou incompatível; nenhum dado foi alterado.\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
