"""Deterministic practice planning and durable review intervals, without AI."""
import time
from .catalog import QUESTIONS
from .plans import entitlement
from fastapi import HTTPException

DAY=86400
INTERVALS=(1,3,7,14,30)
SIZES={15:3,30:6,60:12}

def record_answer(db,uid,qid,correct,now):
    previous=db.execute('SELECT stage FROM review_schedule WHERE user_id=? AND question_id=?',(uid,qid)).fetchone()
    # Correct answers without an earlier error need no remediation schedule.
    if correct and previous is None:return
    stage=min(previous['stage']+1,len(INTERVALS)-1) if correct else 0
    db.execute('INSERT INTO review_schedule(user_id,question_id,stage,due_at,last_answered_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id,question_id) DO UPDATE SET stage=excluded.stage,due_at=excluded.due_at,last_answered_at=excluded.last_answered_at',
        (uid,qid,stage,now+INTERVALS[stage]*DAY,now))


def selection(db,uid,minutes,now):
    if not entitlement(db,uid,now)['active']:raise HTTPException(403,'O planejamento exige plano pago ativo.')
    schedule={r['question_id']:dict(r) for r in db.execute('SELECT * FROM review_schedule WHERE user_id=?',(uid,))}
    performance={r['question_id']:dict(r) for r in db.execute('SELECT question_id,count(*) AS total,sum(correct) AS correct FROM attempts WHERE user_id=? GROUP BY question_id',(uid,))}
    subjects={}
    for q in QUESTIONS:
        if q.id in performance:
            row=performance[q.id];key=(q.area,q.subject)
            total,correct=subjects.get(key,(0,0));subjects[key]=(total+row['total'],correct+row['correct'])
    def priority(q):
        review=schedule.get(q.id)
        if review and review['due_at']<=now:return (0,review['due_at'],q.id)
        total,correct=subjects.get((q.area,q.subject),(0,0))
        if total and correct<total:return (1,correct/total,q.id)
        if q.id not in performance:return (2,0,q.id)
        return (3,0,q.id)
    eligible=[q for q in QUESTIONS if q.id not in schedule or schedule[q.id]['due_at']<=now]
    chosen=sorted(eligible,key=priority)[:SIZES[minutes]]
    reasons=[]
    for q in chosen:
        kind=priority(q)[0]
        reasons.append(dict(question_id=q.id,area=q.area,subject=q.subject,
            reason=('Revisão agendada para agora.','Assunto com erros no seu histórico.','Conteúdo ainda não praticado.','Consolidar conteúdo já praticado.')[kind]))
    due=sum(1 for r in schedule.values() if r['due_at']<=now)
    future=[r['due_at'] for r in schedule.values() if r['due_at']>now]
    return chosen,dict(minutes=minutes,estimated_minutes=minutes,question_count=len(chosen),due_reviews=due,
        next_review_at=min(future) if future else None,reasons=reasons,
        notice='Tempo é uma referência para ritmo, resolução e leitura; não é um cronômetro. Seleção limitada ao catálogo autoral do piloto. Simulados e redação não compõem este plano.')

class Planner:
    def __init__(self,store,clock=time.time):self.store,self.clock=store,clock
    def preview(self,uid,minutes=30):
        with self.store.connect() as db:
            _,plan=selection(db,uid,minutes,int(self.clock()))
            active=db.execute("SELECT id FROM practice_sessions WHERE user_id=? AND status='active'",(uid,)).fetchone()
        return dict(**plan,active_session_id=active['id'] if active else None)
