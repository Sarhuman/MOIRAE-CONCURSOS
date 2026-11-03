import time
import uuid
from datetime import datetime
from decimal import Decimal,InvalidOperation
from fastapi import HTTPException
from .plans import PLANS,entitlement
from .mercadopago import safe_checkout


class Billing:
    def __init__(self,store,provider=None,collector=None,secret=None,origin='',clock=time.time):
        self.store,self.provider,self.collector,self.secret,self.origin,self.clock=store,provider,str(collector or ''),secret,origin,clock

    def ready(self):return self.provider is not None and bool(self.collector and self.secret)

    def catalog(self):return dict(plans=list(PLANS.values()),checkout_enabled=self.ready(),mode='sandbox',renewal='manual',days=30)

    def current(self,user):
        with self.store.connect() as db:
            access=entitlement(db,user,self.clock())
            orders=[dict(r) for r in db.execute('SELECT id,plan_id,amount_cents,status,created_at,refund_requested_at FROM billing_orders WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT 10',(user,))]
        return dict(access=access,orders=orders,checkout_enabled=self.ready(),mode='sandbox')

    def start(self,user,plan_id,key):
        if not self.ready():raise HTTPException(503,'O checkout ainda não está configurado. Nenhuma cobrança foi iniciada.')
        plan=PLANS[plan_id]
        with self.store.connect(write=True) as db:
            if entitlement(db,user,self.clock())['active']:raise HTTPException(409,'Seu plano ainda está ativo. Aguarde o fim do período antes de comprar outro.')
            old=db.execute('SELECT * FROM billing_orders WHERE user_id=? AND request_key=?',(user,key)).fetchone()
            if old:
                if old['plan_id']!=plan_id:raise HTTPException(409,'Solicitação já usada para outro plano.')
                if old['checkout_url']:return dict(order_id=old['id'],checkout_url=old['checkout_url'],mode='sandbox')
                raise HTTPException(409,'Esta solicitação já foi iniciada. Confira o pedido antes de tentar novamente.')
            pending=db.execute("SELECT id FROM billing_orders WHERE user_id=? AND status IN ('preparing','pending','in_process','authorized')",(user,)).fetchone()
            if pending:raise HTTPException(409,'Você já tem um pedido pendente. Confira-o antes de iniciar outro.')
            oid=str(uuid.uuid4());now=int(self.clock())
            db.execute('INSERT INTO billing_orders(id,user_id,plan_id,amount_cents,status,created_at,request_key) VALUES(?,?,?,?,?,?,?)',(oid,user,plan_id,plan['price_cents'],'preparing',now,key))
        try:
            result=self.provider.preference({'id':oid},plan,self.origin);safe_checkout(result['checkout_url'])
        except Exception:
            with self.store.connect(write=True) as db:db.execute("UPDATE billing_orders SET status='failed' WHERE id=?",(oid,))
            raise
        with self.store.connect(write=True) as db:
            db.execute("UPDATE billing_orders SET status='pending',preference_id=?,checkout_url=? WHERE id=?",(result['preference_id'],result['checkout_url'],oid))
        return dict(order_id=oid,checkout_url=result['checkout_url'],mode='sandbox')

    def reconcile(self,payment_id):
        if not self.ready():raise HTTPException(503,'Integração de pagamentos indisponível.')
        # A assinatura só autentica a notificação. O estado é consultado no provedor.
        payment=self.provider.payment(payment_id)
        try:
            updated=datetime.fromisoformat(payment['date_last_updated'].replace('Z','+00:00'))
            if updated.tzinfo is None:raise ValueError()
            version=updated.timestamp()
            cents=Decimal(str(payment['transaction_amount']))*100
            refunded=Decimal(str(payment.get('transaction_amount_refunded',0)))
            if not cents.is_finite() or cents!=cents.to_integral_value() or not refunded.is_finite() or refunded<0:raise ValueError()
            if str(payment['id'])!=payment_id or payment.get('live_mode') is not False or str(payment['collector_id'])!=self.collector or payment['currency_id']!='BRL':raise ValueError()
            reference=str(uuid.UUID(str(payment['external_reference'])));status=payment['status']
        except (KeyError,ValueError,TypeError,InvalidOperation):raise HTTPException(400,'Pagamento não corresponde ao ambiente de teste esperado.')
        with self.store.connect(write=True) as db:
            order=db.execute('SELECT * FROM billing_orders WHERE id=?',(reference,)).fetchone()
            if not order or int(cents)!=order['amount_cents']:raise HTTPException(400,'Pagamento não corresponde ao pedido.')
            if order['payment_id'] and order['payment_id']!=payment_id:raise HTTPException(409,'Outro pagamento já está vinculado ao pedido. É necessária análise.')
            if order['provider_version'] is not None and version<order['provider_version']:return {'ok':True,'ignored':'older_version'}
            # Reembolso parcial/contestação suspende o direito até reconciliação operacional.
            revoked=status in ('refunded','charged_back','cancelled','rejected') or refunded>0 or payment.get('status_detail')=='partially_refunded'
            if order['status'] in ('refunded','charged_back','revoked') and not revoked:return {'ok':True,'ignored':'terminal_state'}
            if order['status']=='needs_review':return {'ok':True,'review_required':True}
            if status=='approved' and not revoked and not db.execute('SELECT 1 FROM access_grants WHERE order_id=?',(order['id'],)).fetchone() and entitlement(db,order['user_id'],self.clock())['active']:
                db.execute("UPDATE billing_orders SET status='needs_review',payment_id=?,provider_version=? WHERE id=?",(payment_id,version,order['id']))
                return {'ok':True,'review_required':True}
            stored='revoked' if revoked else status
            if status not in ('approved','pending','in_process','authorized','rejected','cancelled','refunded','charged_back'):raise HTTPException(400,'Estado de pagamento não suportado.')
            db.execute('UPDATE billing_orders SET payment_id=?,provider_version=?,status=? WHERE id=?',(payment_id,version,stored,order['id']))
            if revoked:
                db.execute("UPDATE access_grants SET status='revoked' WHERE order_id=?",(order['id'],))
            elif status=='approved':
                plan=PLANS[order['plan_id']];now=int(self.clock())
                db.execute("INSERT OR IGNORE INTO access_grants(order_id,user_id,plan_id,starts_at,ends_at,status,essay_credits) VALUES(?,?,?,?,?,'active',?)",(order['id'],order['user_id'],plan['id'],now,now+30*86400,plan['essay_credits']))
                db.execute("UPDATE access_grants SET status='active' WHERE order_id=? AND status='suspended'",(order['id'],))
            else:
                db.execute("UPDATE access_grants SET status='suspended' WHERE order_id=? AND status='active'",(order['id'],))
        return {'ok':True}

    def request_refund(self,user,order_id):
        with self.store.connect(write=True) as db:
            order=db.execute('SELECT * FROM billing_orders WHERE id=? AND user_id=?',(order_id,user)).fetchone()
            if not order:raise HTTPException(404,'Pedido não encontrado.')
            grant=db.execute('SELECT starts_at FROM access_grants WHERE order_id=?',(order_id,)).fetchone()
            now=int(self.clock());within=bool(grant and now<=grant['starts_at']+7*86400)
            db.execute('UPDATE billing_orders SET refund_requested_at=coalesce(refund_requested_at,?) WHERE id=?',(now,order_id))
        return dict(requested=True,within_initial_window=within,message='Pedido registrado para análise. Isso não confirma estorno no Mercado Pago; esta integração está em teste e não possui processamento operacional de reembolso.')
