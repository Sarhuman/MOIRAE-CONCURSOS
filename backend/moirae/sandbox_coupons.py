"""Server-authoritative coupon groundwork, restricted to sandbox and off by default."""
import json
import secrets
import time
from fastapi import HTTPException
from .plans import PLANS


class SandboxCoupons:
    def __init__(self, store, enabled=False, clock=time.time):
        self.store, self.enabled, self.clock = store, enabled, clock

    def guard(self):
        if not self.enabled:
            raise HTTPException(503, 'Campanhas sandbox desativadas. Nenhum cupom real foi emitido.')

    def configure(self, campaign, starts_at, ends_at, valid_seconds, products, outcomes, max_uses):
        """Trusted provisioning, no public management API and no default discounts."""
        self.guard()
        if not isinstance(campaign, str) or not 1 <= len(campaign) <= 80:
            raise ValueError('Campanha inválida.')
        if any(type(n) is not int for n in (starts_at, ends_at, valid_seconds, max_uses)) or ends_at <= starts_at or not 1 <= valid_seconds <= 365*86400 or not 1 <= max_uses <= 1000000:
            raise ValueError('Limites inválidos.')
        if not isinstance(products, list) or not products or len(set(products)) != len(products) or any(p not in PLANS for p in products):
            raise ValueError('Produtos inválidos.')
        if not isinstance(outcomes, list) or not 1 <= len(outcomes) <= 12:
            raise ValueError('Resultados inválidos.')
        for o in outcomes:
            if not isinstance(o, dict) or set(o) != {'discount_bps', 'weight'} or type(o['discount_bps']) is not int or not 0 <= o['discount_bps'] <= 10000 or type(o['weight']) is not int or not 1 <= o['weight'] <= 10000:
                raise ValueError('Probabilidades inválidas.')
        values = (campaign, starts_at, ends_at, valid_seconds, json.dumps(products), json.dumps(outcomes), max_uses)
        with self.store.connect(write=True) as db:
            old = db.execute('SELECT * FROM sandbox_coupon_campaigns WHERE id=?', (campaign,)).fetchone()
            if old:
                if tuple(old[k] for k in ('id','starts_at','ends_at','valid_seconds','products','outcomes','max_uses')) != values:
                    raise HTTPException(409, 'Campanha imutável. Crie outra versão.')
                return
            db.execute('INSERT INTO sandbox_coupon_campaigns(id,starts_at,ends_at,valid_seconds,products,outcomes,max_uses,enabled) VALUES(?,?,?,?,?,?,?,1)', values)

    def campaign(self, db, cid, now):
        row = db.execute('SELECT * FROM sandbox_coupon_campaigns WHERE id=? AND enabled=1 AND starts_at<=? AND ends_at>?', (cid, now, now)).fetchone()
        if not row:
            raise HTTPException(404, 'Campanha indisponível.')
        return row

    def rules(self, cid):
        self.guard()
        with self.store.connect() as db:
            c = self.campaign(db, cid, int(self.clock()))
        outcomes = json.loads(c['outcomes'])
        total = sum(o['weight'] for o in outcomes)
        return dict(sandbox=True, id=cid, starts_at=c['starts_at'], ends_at=c['ends_at'], valid_seconds=c['valid_seconds'], products=json.loads(c['products']),
                    outcomes=[dict(discount_bps=o['discount_bps'], weight=o['weight'], total_weight=total) for o in outcomes], max_uses=c['max_uses'],
                    notice='Uma participação por conta. Uso único, sem acúmulo; cotação de teste, sem pagamento ou desconto real.')

    def draw(self, uid, cid):
        self.guard()
        now = int(self.clock())
        with self.store.connect(write=True) as db:
            c = self.campaign(db, cid, now)
            old = db.execute('SELECT code,discount_bps,expires_at FROM sandbox_coupons WHERE user_id=? AND campaign_id=?', (uid, cid)).fetchone()
            if old:
                return dict(sandbox=True, **dict(old))
            outcomes = json.loads(c['outcomes'])
            ticket = secrets.randbelow(sum(o['weight'] for o in outcomes))
            for o in outcomes:
                ticket -= o['weight']
                if ticket < 0:
                    bps = o['discount_bps']
                    break
            code = 'TEST-' + secrets.token_hex(16).upper()
            expires = min(c['ends_at'], now+c['valid_seconds'])
            db.execute('INSERT INTO sandbox_coupons VALUES(?,?,?,?,?,?)', (code, uid, cid, bps, expires, now))
            return dict(sandbox=True, code=code, discount_bps=bps, expires_at=expires)

    def validated(self, db, uid, code, product, now):
        coupon = db.execute('SELECT * FROM sandbox_coupons WHERE code=? AND user_id=?', (code, uid)).fetchone()
        if not coupon or coupon['expires_at'] <= now:
            raise HTTPException(409, 'Cupom indisponível para esta conta.')
        c = self.campaign(db, coupon['campaign_id'], now)
        if product not in json.loads(c['products']) or product not in PLANS:
            raise HTTPException(409, 'Produto não elegível.')
        if db.execute('SELECT 1 FROM sandbox_coupon_redemptions WHERE code=?', (code,)).fetchone():
            raise HTTPException(409, 'Cupom já utilizado.')
        if c['used_count'] >= c['max_uses']:
            raise HTTPException(409, 'Limite de usos da campanha atingido.')
        base = PLANS[product]['price_cents']
        discount = base*coupon['discount_bps']//10000
        return dict(sandbox=True, product=product, catalog_version=PLANS[product]['catalog_version'], amount_cents=base, discount_cents=discount, total_cents=base-discount, currency='BRL', checkout_available=False)

    def quote(self, uid, code, product):
        self.guard()
        with self.store.connect() as db:
            return self.validated(db, uid, code, product, int(self.clock()))

    def redeem(self, uid, code, product, order_reference):
        """Trusted sandbox adapter only; never accepts client totals or grants access."""
        self.guard()
        if not isinstance(order_reference, str) or not 1 <= len(order_reference) <= 120:
            raise ValueError('Referência inválida.')
        now = int(self.clock())
        with self.store.connect(write=True) as db:
            old = db.execute('SELECT * FROM sandbox_coupon_redemptions WHERE order_reference=?', (order_reference,)).fetchone()
            if old:
                if (old['user_id'], old['code'], old['product']) != (uid, code, product):
                    raise HTTPException(409, 'Referência já utilizada.')
                return json.loads(old['snapshot'])
            result = self.validated(db, uid, code, product, now)
            c = db.execute('SELECT campaign_id FROM sandbox_coupons WHERE code=?', (code,)).fetchone()
            db.execute('INSERT INTO sandbox_coupon_redemptions VALUES(?,?,?,?,?,?,?,?)', (order_reference, uid, code, c['campaign_id'], product, json.dumps(result), now, 'sandbox'))
            db.execute('UPDATE sandbox_coupon_campaigns SET used_count=used_count+1 WHERE id=?', (c['campaign_id'],))
            return result
