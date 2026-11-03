"""Persistent demo workflow. No network, LLM or real correction credit consumption."""
import json
import time
import uuid
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Competency(Strict):
    id: int = Field(ge=1, le=5)
    score: Literal[0, 40, 80, 120, 160, 200]
    explanation: str = Field(min_length=1, max_length=1000)

class Annotation(Strict):
    id: str = Field(min_length=1, max_length=40)
    competency: int = Field(ge=1, le=5)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=500)
    guidance: str = Field(min_length=1, max_length=1000)

class Evaluation(Strict):
    mode: Literal['demonstration']
    rubric_version: Literal['enem-demo-v1']
    notice: str = Field(min_length=1, max_length=500)
    competencies: list[Competency] = Field(min_length=5, max_length=5)
    annotations: list[Annotation] = Field(max_length=20)


def validate_result(value, text):
    result = Evaluation.model_validate(value)
    if {c.id for c in result.competencies} != set(range(1, 6)):
        raise ValueError('Competências duplicadas ou ausentes.')
    if len({a.id for a in result.annotations}) != len(result.annotations):
        raise ValueError('Marcações duplicadas.')
    encoded = text.encode('utf-16-le')
    for a in result.annotations:
        if a.start >= a.end or a.end * 2 > len(encoded):
            raise ValueError('Intervalo inválido.')
        if encoded[a.start * 2:a.end * 2].decode('utf-16-le') != a.quote:
            raise ValueError('Trecho não corresponde ao original.')
    return result.model_dump()


class DemoEvaluator:
    def evaluate(self, theme, text):
        quote = text[:min(80, len(text))]
        return dict(mode='demonstration', rubric_version='enem-demo-v1',
            notice='Demonstração: notas fixas e orientação ilustrativa. Seu texto não foi avaliado por IA.',
            competencies=[dict(id=i, score=120, explanation='Nota fixa de exemplo; não avalia esta competência no seu texto.') for i in range(1,6)],
            annotations=[dict(id='demo-opening', competency=3, start=0, end=len(quote.encode('utf-16-le'))//2,
                quote=quote, guidance='Exercício demonstrativo: reescreva este trecho deixando sua ideia principal mais clara. A reescrita não receberá nota.')])


class Essays:
    def __init__(self, store, enabled=False, evaluator=None, clock=time.time):
        self.store, self.enabled, self.evaluator, self.clock = store, enabled, evaluator or DemoEvaluator(), clock

    def guard(self):
        if not self.enabled:
            raise HTTPException(503, 'Oficina persistente de demonstração desativada neste ambiente.')

    def own(self, db, uid, eid):
        row = db.execute('SELECT * FROM essay_submissions WHERE id=? AND user_id=?', (eid, uid)).fetchone()
        if not row:
            raise HTTPException(404, 'Redação não encontrada.')
        return row

    def balance(self, db, uid):
        grant = db.execute("SELECT * FROM access_grants WHERE user_id=? AND status='active' AND starts_at<=? AND ends_at>? ORDER BY starts_at DESC LIMIT 1", (uid, int(self.clock()), int(self.clock()))).fetchone()
        if not grant:
            raise HTTPException(403, 'O envio exige plano pago ativo no piloto. Correção real ainda indisponível.')
        used = db.execute("SELECT count(*) FROM essay_submissions WHERE grant_id=? AND status IN ('received','processing','completed')", (grant['order_id'],)).fetchone()[0]
        return grant, max(0, grant['essay_credits'] - used)

    def submit(self, uid, key, theme, text):
        self.guard()
        with self.store.connect(write=True) as db:
            old = db.execute('SELECT * FROM essay_submissions WHERE user_id=? AND request_key=?', (uid,key)).fetchone()
            if old:
                if old['theme'] != theme or old['text'] != text:
                    raise HTTPException(409, 'Identificador já usado com outro texto.')
                return dict(id=old['id'],status=old['status'],mode='demonstration')
            grant, remaining = self.balance(db,uid)
            if not remaining:
                raise HTTPException(409, 'Créditos de demonstração esgotados neste acesso.')
            eid = str(uuid.uuid4())
            db.execute("INSERT INTO essay_submissions(id,user_id,grant_id,request_key,theme,text,status,created_at) VALUES(?,?,?,?,?,?,'received',?)", (eid,uid,grant['order_id'],key,theme,text,int(self.clock())))
            return dict(id=eid,status='received',mode='demonstration')

    def process(self, uid, eid):
        self.guard()
        # Transaction is deliberately held only for the local, non-network evaluator.
        # A future remote provider requires a leased worker and durable queue.
        with self.store.connect(write=True) as db:
            row = self.own(db,uid,eid)
            if row['status'] != 'received':
                return dict(id=eid,status=row['status'])
            grant = db.execute("SELECT 1 FROM access_grants WHERE order_id=? AND status='active' AND ends_at>?", (row['grant_id'],int(self.clock()))).fetchone()
            if not grant:
                db.execute("UPDATE essay_submissions SET status='failed',error='access_expired' WHERE id=?", (eid,))
                return dict(id=eid,status='failed')
            db.execute("UPDATE essay_submissions SET status='processing' WHERE id=?", (eid,))
            try:
                result = validate_result(self.evaluator.evaluate(row['theme'],row['text']), row['text'])
            except Exception:
                db.execute("UPDATE essay_submissions SET status='failed',error='evaluation_unavailable' WHERE id=?", (eid,))
                return dict(id=eid,status='failed')
            db.execute("UPDATE essay_submissions SET status='completed',result=? WHERE id=?", (json.dumps(result,ensure_ascii=False),eid))
        return dict(id=eid,status='completed')

    def detail(self,uid,eid):
        self.guard()
        with self.store.connect() as db:
            row=dict(self.own(db,uid,eid))
            rewrites=[dict(r) for r in db.execute('SELECT id,annotation_id,text,created_at FROM essay_rewrites WHERE essay_id=? ORDER BY created_at,id',(eid,))]
        return dict(id=eid,theme=row['theme'],text=row['text'],status=row['status'],created_at=row['created_at'],
                    result=json.loads(row['result']) if row['result'] else None,error=row['error'],rewrites=rewrites,mode='demonstration')

    def history(self,uid):
        self.guard()
        with self.store.connect() as db:
            rows=[dict(r) for r in db.execute('SELECT id,theme,status,created_at FROM essay_submissions WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 100',(uid,))]
            try: _, remaining=self.balance(db,uid)
            except HTTPException: remaining=0
        return dict(items=rows,remaining=remaining,mode='demonstration',notice='Créditos de teste separados das futuras correções reais. Histórico mostra até 100 envios recentes.')

    def rewrite(self,uid,eid,key,annotation,text):
        self.guard()
        with self.store.connect(write=True) as db:
            row=self.own(db,uid,eid)
            old=db.execute('SELECT * FROM essay_rewrites WHERE essay_id=? AND request_key=?',(eid,key)).fetchone()
            if old:
                if old['text'] != text or old['annotation_id'] != annotation:
                    raise HTTPException(409,'Identificador já usado com outra reescrita.')
                return dict(id=old['id'])
            if row['status'] != 'completed': raise HTTPException(409,'Aguarde o resultado antes de reescrever.')
            if annotation not in {a['id'] for a in json.loads(row['result'])['annotations']}:
                raise HTTPException(422,'Marcação inválida.')
            if db.execute('SELECT count(*) FROM essay_rewrites WHERE essay_id=?',(eid,)).fetchone()[0]>=10:
                raise HTTPException(409,'Limite de dez reescritas por demonstração.')
            rid=str(uuid.uuid4())
            db.execute('INSERT INTO essay_rewrites VALUES(?,?,?,?,?,?)',(rid,eid,annotation,key,text,int(self.clock())))
        return dict(id=rid)
