"""Private review of accepted practice answers; no new attempt or quota debit."""
from fastapi import HTTPException
from .catalog import BY_ID
from .plans import entitlement

class Review:
    def __init__(self,store):self.store=store

    def guard(self,db,uid):
        if not entitlement(db,uid)['active']:
            raise HTTPException(403,'O caderno exige um plano pago ativo.')

    def listing(self,uid,view='errors'):
        with self.store.connect() as db:
            self.guard(db,uid)
            condition={'errors':'had_error=1','favorites':'favorite=1','all':'1=1'}[view]
            # Bound the response; compute the latest answer and error history in SQL.
            rows=db.execute(f"""WITH ranked AS (
                SELECT a.question_id,a.choice,a.correct,a.created_at,
                row_number() OVER(PARTITION BY a.question_id ORDER BY a.created_at DESC,a.rowid DESC) AS position,
                max(CASE WHEN a.correct=0 THEN 1 ELSE 0 END) OVER(PARTITION BY a.question_id) AS had_error,
                EXISTS(SELECT 1 FROM review_favorites f WHERE f.user_id=a.user_id AND f.question_id=a.question_id) AS favorite
                FROM attempts a WHERE a.user_id=?
            ) SELECT *,count(*) OVER() AS total FROM ranked WHERE position=1 AND {condition}
              ORDER BY created_at DESC,question_id LIMIT 100""",(uid,)).fetchall()
        items=[]
        for row in rows:
            qid=row['question_id']
            if qid not in BY_ID:continue
            q=BY_ID[qid]
            items.append(dict(question=q.public(),answer=q.answer,explanation=q.explanation,
                last_choice=row['choice'],last_correct=bool(row['correct']),had_error=bool(row['had_error']),
                favorite=bool(row['favorite']),last_answered_at=row['created_at']))
        return dict(items=items,total=rows[0]['total'] if rows else 0,limit=100,view=view,
            notice='Respostas de prática aceitas, até 100 questões por consulta. Simulados ainda não integram este caderno. Consultar não consome sua cota.')

    def favorite(self,uid,qid,enabled):
        with self.store.connect(write=True) as db:
            self.guard(db,uid)
            if qid not in BY_ID or not db.execute('SELECT 1 FROM attempts WHERE user_id=? AND question_id=?',(uid,qid)).fetchone():
                raise HTTPException(404,'Questão respondida não encontrada.')
            if enabled:
                db.execute('INSERT OR IGNORE INTO review_favorites(user_id,question_id) VALUES(?,?)',(uid,qid))
            else:db.execute('DELETE FROM review_favorites WHERE user_id=? AND question_id=?',(uid,qid))
        return dict(question_id=qid,favorite=enabled)
