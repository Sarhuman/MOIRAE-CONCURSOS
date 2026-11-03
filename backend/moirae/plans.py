"""Catálogo e permissões definidos exclusivamente no servidor."""
import time

PLANS={
 'essencial':dict(id='essencial',name='Essencial',price_cents=3500,currency='BRL',days=30,essay_credits=3),
 'avancado':dict(id='avancado',name='Avançado',price_cents=5500,currency='BRL',days=30,essay_credits=8),
}


def entitlement(db,user,now=None):
    now=int(time.time()) if now is None else int(now)
    row=db.execute("SELECT * FROM access_grants WHERE user_id=? AND status='active' AND starts_at<=? AND ends_at>? ORDER BY starts_at DESC LIMIT 1",(user,now,now)).fetchone()
    if not row:return dict(plan='free',active=False,ends_at=None,essay_credits=0)
    return dict(plan=row['plan_id'],active=True,ends_at=row['ends_at'],essay_credits=row['essay_credits'])
