import json
import secrets
import time
import uuid
from fastapi import HTTPException
from .catalog import BY_ID, QUESTIONS
from .domain import SESSION_SIZE, study_day
from .quota import monthly_quota
from .planner import selection,record_answer


class Practice:
    def __init__(self, store, clock=study_day):
        self.store, self.clock = store, clock

    def quota(self, db, user):
        return monthly_quota(db,user,self.clock())

    def snapshot(self, db, user, row):
        count = db.execute('SELECT count(*) FROM attempts WHERE session_id=?',(row['id'],)).fetchone()[0]
        total = db.execute('SELECT count(*) FROM session_questions WHERE session_id=?',(row['id'],)).fetchone()[0]
        next_row = db.execute('SELECT question_id FROM session_questions WHERE session_id=? AND position=?',(row['id'],count)).fetchone()
        plan=db.execute('SELECT minutes,description FROM practice_plans WHERE session_id=?',(row['id'],)).fetchone()
        return dict(plan=json.loads(plan['description']) if plan else None,id=row['id'],status=row['status'],answered=count,total=total,
                    question=BY_ID[next_row[0]].public() if next_row else None,quota=self.quota(db,user))

    def start(self, user, minutes=None):
        with self.store.connect(write=True) as db:
            planned=None
            if minutes is not None:
                selected,planned=selection(db,user,minutes,int(time.time()))
            row = db.execute("SELECT * FROM practice_sessions WHERE user_id=? AND status='active'",(user,)).fetchone()
            if row:
                return self.snapshot(db,user,row)
            quota=self.quota(db,user)
            if not quota['unlimited'] and not quota['remaining']:
                raise HTTPException(429,'Você usou suas 30 questões deste mês. Aguarde a renovação mensal.')
            sid=str(uuid.uuid4())
            # Cobrir áreas com seleção embaralhada de conteúdo introdutório.
            baseline=[]
            for area in ('Matemática','Linguagens','Natureza','Humanas'):
                baseline.append(secrets.choice([q for q in QUESTIONS if q.area==area]))
            baseline.append(secrets.choice([q for q in QUESTIONS if q not in baseline]))
            if minutes is None:selected=baseline[:SESSION_SIZE if quota['unlimited'] else min(SESSION_SIZE,quota['remaining'])]
            if not selected:raise HTTPException(409,'Não há revisões vencidas ou questões elegíveis agora. Consulte o próximo agendamento no painel.')
            db.execute('INSERT INTO practice_sessions VALUES(?,?,?,?)',(sid,user,'active',int(time.time())))
            if planned is not None:db.execute('INSERT INTO practice_plans VALUES(?,?,?)',(sid,minutes,json.dumps(planned)))
            db.executemany('INSERT INTO session_questions VALUES(?,?,?)',[(sid,i,q.id) for i,q in enumerate(selected)])
            return self.snapshot(db,user,db.execute('SELECT * FROM practice_sessions WHERE id=?',(sid,)).fetchone())

    def current(self,user):
        with self.store.connect() as db:
            row=db.execute("SELECT * FROM practice_sessions WHERE user_id=? AND status='active'",(user,)).fetchone()
            return dict(session=self.snapshot(db,user,row) if row else None,quota=self.quota(db,user))

    def answer(self,user,sid,question_id,choice,key):
        payload=json.dumps([sid,question_id,choice],separators=(',',':'))
        with self.store.connect(write=True) as db:
            previous=db.execute('SELECT * FROM idempotency WHERE user_id=? AND key=?',(user,key)).fetchone()
            if previous:
                if previous['payload']!=payload:
                    raise HTTPException(409,'Esta tentativa já foi usada para outra resposta.')
                result=json.loads(previous['response'])
                result['session']['quota']=self.quota(db,user)
                return result
            row=db.execute('SELECT * FROM practice_sessions WHERE id=? AND user_id=?',(sid,user)).fetchone()
            if not row:
                raise HTTPException(404,'Atividade não encontrada.')
            if row['status']!='active':
                raise HTTPException(409,'Esta atividade já terminou. Inicie outra para continuar.')
            count=db.execute('SELECT count(*) FROM attempts WHERE session_id=?',(sid,)).fetchone()[0]
            expected=db.execute('SELECT question_id FROM session_questions WHERE session_id=? AND position=?',(sid,count)).fetchone()
            if not expected or expected[0]!=question_id:
                raise HTTPException(409,'A questão mudou ou já foi respondida. Atualize a atividade.')
            quota=self.quota(db,user)
            if not quota['unlimited'] and not quota['remaining']:
                raise HTTPException(429,'Limite mensal atingido. Sua atividade foi preservada para o próximo mês.')
            question=BY_ID[question_id]
            if choice not in [chr(97+i) for i in range(len(question.options))]:
                raise HTTPException(422,'Alternativa inválida.')
            correct=choice==question.answer
            db.execute('INSERT INTO attempts(id,user_id,session_id,question_id,choice,correct,day,created_at,free_charge) VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),user,sid,question_id,choice,int(correct),quota['day'],int(time.time()),int(not quota['unlimited'])))
            record_answer(db,user,question_id,correct,int(time.time()))
            total=db.execute('SELECT count(*) FROM session_questions WHERE session_id=?',(sid,)).fetchone()[0]
            if count+1==total:
                db.execute("UPDATE practice_sessions SET status='completed' WHERE id=?",(sid,))
            row=db.execute('SELECT * FROM practice_sessions WHERE id=?',(sid,)).fetchone()
            scheduled=db.execute('SELECT stage,due_at FROM review_schedule WHERE user_id=? AND question_id=?',(user,question_id)).fetchone()
            result=dict(review_schedule=dict(scheduled) if scheduled else None,correct=correct,answer=question.answer,explanation=question.explanation,
                        session=self.snapshot(db,user,row))
            # O resultado da atividade atual não é um dashboard histórico.
            if row['status']=='completed':
                result['summary']=dict(total=total,correct=db.execute('SELECT sum(correct) FROM attempts WHERE session_id=?',(sid,)).fetchone()[0])
            db.execute('INSERT INTO idempotency VALUES(?,?,?,?)',(user,key,payload,json.dumps(result)))
            return result
