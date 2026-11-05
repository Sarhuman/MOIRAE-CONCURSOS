"""Sandbox-only lots, isolated from real essay credits."""
import time
import uuid
from contextlib import contextmanager
from fastapi import HTTPException


class SandboxWallet:
    def __init__(self, store, enabled=False, clock=time.time):
        self.store, self.enabled, self.clock = store, enabled, clock

    @contextmanager
    def transaction(self, existing=None):
        # Caller-owned transactions make essay insertion and reservation atomic.
        if existing is not None:
            yield existing
        else:
            with self.store.connect(write=True) as db:
                yield db

    def guard(self):
        if not self.enabled:
            raise HTTPException(503, 'Carteira sandbox desativada. Nenhum crédito real foi alterado.')

    def grant(self, uid, source, units, expires_at, db=None):
        """Trusted provisioning/payment reconciliation; never accept client balance input."""
        self.guard()
        now = int(self.clock())
        if not isinstance(source, str) or not 1 <= len(source) <= 120 or type(units) is not int or not 1 <= units <= 10000 or type(expires_at) is not int or expires_at <= now:
            raise ValueError('Lote inválido.')
        with self.transaction(db) as db:
            old = db.execute('SELECT * FROM sandbox_credit_lots WHERE source=?', (source,)).fetchone()
            if old:
                if (old['user_id'], old['units'], old['expires_at']) != (uid, units, expires_at):
                    raise HTTPException(409, 'Origem já utilizada para outro lote.')
                return old['id']
            lid = str(uuid.uuid4())
            db.execute('INSERT INTO sandbox_credit_lots VALUES(?,?,?,?,?,?,0,0,?,NULL)', (lid, uid, source, units, units, expires_at, now))
            self.event(db, uid, lid, 'grant', lid, units, now)
            return lid

    @staticmethod
    def event(db, uid, lid, kind, reference, units, now):
        db.execute('INSERT INTO sandbox_wallet_events(user_id,lot_id,kind,reference,units,created_at) VALUES(?,?,?,?,?,?)', (uid, lid, kind, reference, units, now))

    def reserve(self, uid, key, db=None):
        self.guard()
        if not isinstance(key, str) or not 1 <= len(key) <= 120:
            raise ValueError('Identificador inválido.')
        now = int(self.clock())
        with self.transaction(db) as db:
            old = db.execute('SELECT * FROM sandbox_credit_reservations WHERE user_id=? AND request_key=?', (uid, key)).fetchone()
            if old:
                return dict(old)
            lot = db.execute('SELECT * FROM sandbox_credit_lots WHERE user_id=? AND revoked_at IS NULL AND expires_at>? AND available>0 ORDER BY expires_at,created_at,id LIMIT 1', (uid, now)).fetchone()
            if not lot:
                raise HTTPException(409, 'Sem créditos sandbox disponíveis.')
            rid = str(uuid.uuid4())
            db.execute('UPDATE sandbox_credit_lots SET available=available-1,reserved=reserved+1 WHERE id=?', (lot['id'],))
            db.execute("INSERT INTO sandbox_credit_reservations VALUES(?,?,?,?,'reserved',?)", (rid, uid, lot['id'], key, now))
            self.event(db, uid, lot['id'], 'reserve', rid, 1, now)
            return dict(db.execute('SELECT * FROM sandbox_credit_reservations WHERE id=?', (rid,)).fetchone())

    def settle(self, uid, rid, action, db=None):
        self.guard()
        if action not in ('consume', 'release', 'refund'):
            raise ValueError('Operação inválida.')
        target = {'consume': 'consumed', 'release': 'released', 'refund': 'refunded'}[action]
        expected = 'consumed' if action == 'refund' else 'reserved'
        now = int(self.clock())
        with self.transaction(db) as db:
            r = db.execute('SELECT * FROM sandbox_credit_reservations WHERE id=? AND user_id=?', (rid, uid)).fetchone()
            if not r:
                raise HTTPException(404, 'Reserva não encontrada.')
            if r['status'] == target:
                return dict(r)
            if r['status'] != expected:
                raise HTTPException(409, 'Reserva já encerrada por outra operação.')
            lot = db.execute('SELECT * FROM sandbox_credit_lots WHERE id=?', (r['lot_id'],)).fetchone()
            if action == 'consume' and (lot['revoked_at'] is not None or lot['expires_at'] <= now):
                raise HTTPException(409, 'Lote vencido ou revogado; libere a reserva.')
            if action == 'consume':
                db.execute('UPDATE sandbox_credit_lots SET reserved=reserved-1,consumed=consumed+1 WHERE id=?', (lot['id'],))
            elif action == 'release':
                db.execute('UPDATE sandbox_credit_lots SET reserved=reserved-1,available=available+1 WHERE id=?', (lot['id'],))
            else:
                db.execute('UPDATE sandbox_credit_lots SET consumed=consumed-1,available=available+1 WHERE id=?', (lot['id'],))
            db.execute('UPDATE sandbox_credit_reservations SET status=? WHERE id=?', (target, rid))
            self.event(db, uid, lot['id'], action, rid, 1, now)
            return dict(db.execute('SELECT * FROM sandbox_credit_reservations WHERE id=?', (rid,)).fetchone())

    def revoke(self, uid, lid, db=None):
        """Trusted sandbox refund/chargeback signal; never revives expired credits."""
        self.guard()
        now = int(self.clock())
        with self.transaction(db) as db:
            lot = db.execute('SELECT * FROM sandbox_credit_lots WHERE id=? AND user_id=?', (lid, uid)).fetchone()
            if not lot:
                raise HTTPException(404, 'Lote não encontrado.')
            if lot['revoked_at'] is not None:
                return
            db.execute('UPDATE sandbox_credit_lots SET revoked_at=? WHERE id=?', (now, lid))
            pending = db.execute("SELECT id FROM sandbox_credit_reservations WHERE lot_id=? AND status='reserved'", (lid,)).fetchall()
            for row in pending:
                db.execute("UPDATE sandbox_credit_reservations SET status='released' WHERE id=?", (row['id'],))
                self.event(db, uid, lid, 'release', row['id'], 1, now)
            db.execute('UPDATE sandbox_credit_lots SET available=available+reserved,reserved=0 WHERE id=?', (lid,))
            self.event(db, uid, lid, 'revoke', lid, lot['units'], now)

    def snapshot(self, uid):
        self.guard()
        now = int(self.clock())
        with self.store.connect() as db:
            lots = [dict(r) for r in db.execute('SELECT id,units,available,reserved,consumed,expires_at,revoked_at FROM sandbox_credit_lots WHERE user_id=? ORDER BY expires_at,id', (uid,))]
            events = [dict(r) for r in db.execute('SELECT kind,lot_id,reference,units,created_at FROM sandbox_wallet_events WHERE user_id=? ORDER BY id DESC LIMIT 100', (uid,))]
        for lot in lots:
            lot['status'] = 'revoked' if lot['revoked_at'] is not None else 'expired' if lot['expires_at'] <= now else 'active'
        return dict(sandbox=True, available=sum(l['available'] for l in lots if l['status'] == 'active'), lots=lots, events=events,
                    notice='Créditos de teste para a oficina demonstrativa, sem valor monetário. Não representam avaliação por IA ou correção real. A oficina exige plano ativo no piloto.')
