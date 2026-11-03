"""Simulado curto autoral; o servidor decide prazo, conteúdo e consumo."""
import random
import time
import uuid
from fastapi import HTTPException
from .catalog import QUESTIONS, BY_ID
from .domain import study_day
from .quota import monthly_quota

PROFILES={1:{'duration':1800,'areas':('Linguagens','Humanas')},2:{'duration':900,'areas':('Matemática','Natureza')}}
ESSAY={
    'title':'O acesso à internet e as oportunidades de aprendizagem no Brasil',
    'instructions':'Escreva um texto dissertativo-argumentativo sobre o tema. Apresente seu ponto de vista, desenvolva os argumentos e proponha uma intervenção. Este treino digitado não reproduz a folha manuscrita nem permite contar linhas oficiais.',
    'supporting_texts':[
        'Texto autoral 1: Uma atividade de pesquisa pode depender de conexão, equipamento e de um espaço adequado para estudar. Ter acesso à internet, por si só, não resolve todas essas necessidades.',
        'Texto autoral 2: Bibliotecas e escolas podem oferecer espaços de acesso e orientação. Ao planejar essas ações, é preciso considerar as condições de cada comunidade.'
    ],
    'notice':'Tema e textos motivadores autorais para demonstração. O Free salva o texto, mas não inclui correção, nota ou envio à OpenAI.'
}


class Exams:
    def __init__(self,store,clock=time.time):self.store,self.clock=store,clock

    def day_now(self):
        from datetime import datetime,timezone
        return study_day(datetime.fromtimestamp(self.clock(),timezone.utc))

    def expire(self,db,user):
        db.execute("UPDATE mock_exams SET status='expired' WHERE user_id=? AND status='active' AND deadline<=?",(user,int(self.clock())))

    def own(self,db,user,exam_id):
        row=db.execute('SELECT * FROM mock_exams WHERE id=? AND user_id=?',(exam_id,user)).fetchone()
        if not row:raise HTTPException(404,'Simulado não encontrado.')
        return row

    def snapshot(self,db,row):
        items=[];correct=0;answered=0
        for item in db.execute('SELECT * FROM mock_items WHERE exam_id=? ORDER BY position',(row['id'],)):
            q=BY_ID[item['question_id']];entry=dict(question=q.public(),choice=item['choice'],flagged=bool(item['flagged']),revision=item['revision'])
            if item['choice']:answered+=1
            if row['status']!='active':
                entry.update(answer=q.answer,explanation=q.explanation,correct=item['choice']==q.answer)
                correct+=int(item['choice']==q.answer)
            items.append(entry)
        result=dict(id=row['id'],day=row['day'],status=row['status'],started_at=row['started_at'],deadline=row['deadline'],
                    server_now=int(self.clock()),items=items,answered=answered,essay=row['essay'],essay_revision=row['essay_revision'],
                    essay_prompt=ESSAY if row['day']==1 else None,quota=monthly_quota(db,row['user_id'],self.day_now()),
                    note='Simulado autoral curto de teste; não é uma prova oficial completa do ENEM.')
        if row['status']!='active':
            result['result']=dict(correct=correct,total=len(items),blank=len(items)-answered,essay_status='saved_without_correction' if row['day']==1 else 'not_applicable')
        return result

    def current(self,user):
        with self.store.connect(write=True) as db:
            self.expire(db,user)
            # Só a tentativa atual/mais recente: não é uma consulta ao histórico Free.
            row=db.execute('SELECT * FROM mock_exams WHERE user_id=? ORDER BY started_at DESC,rowid DESC LIMIT 1',(user,)).fetchone()
            return dict(exam=self.snapshot(db,row) if row else None,quota=monthly_quota(db,user,self.day_now()))

    def start(self,user,day,key):
        with self.store.connect(write=True) as db:
            self.expire(db,user)
            previous=db.execute('SELECT * FROM mock_exams WHERE user_id=? AND start_key=?',(user,key)).fetchone()
            if previous:
                if previous['day']!=day:raise HTTPException(409,'Esta solicitação já foi usada para outro simulado.')
                return self.snapshot(db,previous)
            active=db.execute("SELECT * FROM mock_exams WHERE user_id=? AND status='active'",(user,)).fetchone()
            if active:
                if active['day']!=day:raise HTTPException(409,'Encerre o simulado em andamento antes de iniciar outro.')
                return self.snapshot(db,active)
            profile=PROFILES[day];selected=[q for q in QUESTIONS if q.area in profile['areas']]
            quota=monthly_quota(db,user,self.day_now())
            if quota['remaining']<len(selected):raise HTTPException(429,f"Este simulado usa {len(selected)} questões. Seu saldo é {quota['remaining']}.")
            random.SystemRandom().shuffle(selected)
            now=int(self.clock());eid=str(uuid.uuid4())
            # Debitar o caderno ao iniciar impede alternar entre simulados para contornar a cota.
            # A confirmação na interface informa o consumo, inclusive se houver abandono.
            db.execute('INSERT INTO mock_exams(id,user_id,day,started_at,deadline,status,charged_questions,quota_period,start_key) VALUES(?,?,?,?,?,?,?,?,?)',
                       (eid,user,day,now,now+profile['duration'],'active',len(selected),quota['period'],key))
            db.executemany('INSERT INTO mock_items(exam_id,position,question_id) VALUES(?,?,?)',[(eid,i,q.id) for i,q in enumerate(selected)])
            return self.snapshot(db,self.own(db,user,eid))

    def save_item(self,user,eid,qid,choice,flagged,revision):
        with self.store.connect(write=True) as db:
            self.expire(db,user);row=self.own(db,user,eid)
            if row['status']!='active':return self.snapshot(db,row)
            item=db.execute('SELECT * FROM mock_items WHERE exam_id=? AND question_id=?',(eid,qid)).fetchone()
            if not item:raise HTTPException(404,'Questão não pertence ao simulado.')
            # Replay idêntico após perda de rede não gera conflito ou novo consumo.
            if item['choice']==choice and bool(item['flagged'])==flagged and revision<=item['revision']:
                return self.snapshot(db,row)
            if item['revision']!=revision:raise HTTPException(409,'Resposta alterada em outra aba. Atualize o simulado antes de salvar.')
            db.execute('UPDATE mock_items SET choice=?,flagged=?,revision=revision+1 WHERE exam_id=? AND question_id=?',(choice,int(flagged),eid,qid))
            return self.snapshot(db,row)

    def save_essay(self,user,eid,text,revision):
        with self.store.connect(write=True) as db:
            self.expire(db,user);row=self.own(db,user,eid)
            if row['status']!='active':return self.snapshot(db,row)
            if row['day']!=1:raise HTTPException(422,'Esta atividade não inclui redação.')
            if row['essay']==text and revision<=row['essay_revision']:return self.snapshot(db,row)
            if row['essay_revision']!=revision:raise HTTPException(409,'Redação alterada em outra aba. Copie seu rascunho antes de atualizar.')
            db.execute('UPDATE mock_exams SET essay=?,essay_revision=essay_revision+1 WHERE id=?',(text,eid))
            return self.snapshot(db,self.own(db,user,eid))

    def finish(self,user,eid):
        with self.store.connect(write=True) as db:
            self.expire(db,user);row=self.own(db,user,eid)
            if row['status']=='active':db.execute("UPDATE mock_exams SET status='submitted' WHERE id=?",(eid,))
            return self.snapshot(db,self.own(db,user,eid))
