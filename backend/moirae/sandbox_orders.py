"""Contracts attached to Billing orders; uses the existing wallet and coupon ledger."""
import json
from fastapi import HTTPException
from .commercial import catalog, quote


class SandboxOrders:
    HOLD_SECONDS = 30*60  # Technical reservation timeout, not coupon validity.

    def __init__(self, wallet, coupons, pack_validity_days=None):
        if pack_validity_days is not None and (type(pack_validity_days) is not int or not 1 <= pack_validity_days <= 365):
            raise ValueError('Validade sandbox dos pacotes inválida.')
        self.wallet,self.coupons,self.pack_validity_days=wallet,coupons,pack_validity_days

    def pack(self, product):
        self.wallet.guard()
        if self.pack_validity_days is None:
            raise HTTPException(503,'Compra de créditos sandbox bloqueada: validade dos pacotes ainda não aprovada/configurada.')
        p=next((p for p in catalog()['credit_packs'] if p['id']==product),None)
        if not p:raise HTTPException(404,'Pacote inexistente.')
        q=quote(product)
        return dict(id=product,name=f"{p['credits']} créditos sandbox",price_cents=q['product_total_cents'],essay_credits=p['credits'],days=0,catalog_version=catalog()['version'])

    def attach(self, db, user, oid, plan, kind, code, now):
        expires=now+self.HOLD_SECONDS
        snapshot=dict(product=plan['id'],amount_cents=plan['price_cents'],discount_cents=0,total_cents=plan['price_cents'],currency='BRL',catalog_version=plan['catalog_version'])
        if kind=='credit_pack':
            snapshot.update(credits=plan['essay_credits'],validity_days=self.pack_validity_days,quote=quote(plan['id']))
        if code:
            snapshot,expires=self.coupons.hold(db,user,code,plan['id'],oid,expires)
        db.execute("INSERT INTO sandbox_order_contracts(order_id,user_id,kind,snapshot,expires_at,state,coupon_code) VALUES(?,?,?,?,?,'pending',?)",(oid,user,kind,json.dumps(snapshot),expires,code))
        db.execute('UPDATE billing_orders SET amount_cents=? WHERE id=?',(snapshot['total_cents'],oid))
        return snapshot['total_cents']

    def expire(self, db, user, now):
        rows=db.execute("SELECT order_id FROM sandbox_order_contracts WHERE user_id=? AND state='pending' AND expires_at<=?",(user,now)).fetchall()
        for row in rows:
            db.execute("UPDATE sandbox_order_contracts SET state='expired' WHERE order_id=?",(row['order_id'],))
            db.execute("UPDATE billing_orders SET status='expired' WHERE id=? AND status IN ('preparing','pending','in_process','authorized')",(row['order_id'],))
            self.coupons.release_hold(db,row['order_id'])

    def cancel(self, db, uid, oid):
        row=db.execute('SELECT * FROM sandbox_order_contracts WHERE order_id=? AND user_id=?',(oid,uid)).fetchone()
        if not row:raise HTTPException(404,'Pedido sandbox não encontrado.')
        if row['state'] not in ('pending','expired','cancelled'):raise HTTPException(409,'Pedido já liquidado ou em análise. Solicite análise de reembolso.')
        db.execute("UPDATE sandbox_order_contracts SET state='cancelled' WHERE order_id=?",(oid,))
        db.execute("UPDATE billing_orders SET status='cancelled' WHERE id=?",(oid,))
        self.coupons.release_hold(db,oid)

    def review(self, db, order, reason):
        db.execute("UPDATE sandbox_order_contracts SET state='needs_review',review_reason=? WHERE order_id=?",(reason,order['id']))
        db.execute("UPDATE billing_orders SET status='needs_review' WHERE id=?",(order['id'],))
        self.coupons.release_hold(db,order['id'])

    def reconcile(self, db, order, status, revoked, now, partial=False):
        """Return None for legacy orders, otherwise a server-authorized result."""
        contract=db.execute('SELECT * FROM sandbox_order_contracts WHERE order_id=?',(order['id'],)).fetchone()
        if not contract:return None
        if revoked:
            db.execute("UPDATE access_grants SET status='revoked' WHERE order_id=?",(order['id'],))
            consumed=0
            if contract['lot_id']:
                lot=db.execute('SELECT * FROM sandbox_credit_lots WHERE id=?',(contract['lot_id'],)).fetchone()
                self.wallet.revoke(order['user_id'],lot['id'],db=db)
                consumed=lot['consumed']
            if consumed or partial:
                self.review(db,order,'Reembolso com consumo ou valor parcial: decisão monetária manual pendente.')
                return dict(ok=True,review_required=True)
            db.execute("UPDATE sandbox_order_contracts SET state='revoked' WHERE order_id=?",(order['id'],))
            self.coupons.release_hold(db,order['id'])
            return dict(ok=True)
        if contract['state'] in ('needs_review','revoked'):
            return dict(ok=True,review_required=contract['state']=='needs_review')
        if status!='approved':
            # A paid lot must never remain spendable after a non-final provider regression.
            if contract['state']=='fulfilled':
                if contract['lot_id']:self.wallet.revoke(order['user_id'],contract['lot_id'],db=db)
                db.execute("UPDATE access_grants SET status='suspended' WHERE order_id=?",(order['id'],))
                self.review(db,order,'Estado do provedor regrediu após concessão.')
                return dict(ok=True,review_required=True)
            return dict(ok=True)
        if contract['state']=='fulfilled':return dict(ok=True)
        if contract['state']!='pending' or contract['expires_at']<=now:
            self.review(db,order,'Pagamento confirmado após encerramento da reserva técnica.')
            return dict(ok=True,review_required=True)
        snapshot=json.loads(contract['snapshot'])
        if contract['coupon_code']:
            try:self.coupons.commit_hold(db,order['user_id'],contract['coupon_code'],order['plan_id'],order['id'],snapshot)
            except HTTPException:
                self.review(db,order,'Reserva de cupom indisponível na confirmação do pagamento.')
                return dict(ok=True,review_required=True)
        if contract['kind']=='credit_pack':
            lid=self.wallet.grant(order['user_id'],'billing-sandbox:'+order['id'],snapshot['credits'],now+snapshot['validity_days']*86400,db=db)
            db.execute("UPDATE sandbox_order_contracts SET state='fulfilled',lot_id=? WHERE order_id=?",(lid,order['id']))
        else:
            # Billing owns access grants; allow its normal plan fulfillment in this transaction.
            db.execute("UPDATE sandbox_order_contracts SET state='fulfilled' WHERE order_id=?",(order['id'],))
            return None
        return dict(ok=True)
