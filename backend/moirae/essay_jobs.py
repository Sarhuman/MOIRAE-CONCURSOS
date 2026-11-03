"""Durable SQLite queue, fenced leases and a real-credit ledger, separate from demos."""
import json
import time
import uuid
from fastapi import HTTPException
from .plans import entitlement
from .essay_provider import RUBRIC,PROMPT,ProviderFailure,canonical

class EssayJobs:
    def __init__(self,store,enabled=False,model='',clock=time.time):
        self.store,self.enabled,self.model,self.clock=store,enabled,model,clock
    def guard(self):
        if not self.enabled or not self.model:raise HTTPException(503,'Correção automatizada real ainda não habilitada. Nenhum crédito foi reservado.')
    def balance(self,db,uid):
        now=int(self.clock())
        grant=db.execute("SELECT * FROM access_grants WHERE user_id=? AND status='active' AND starts_at<=? AND ends_at>? ORDER BY starts_at DESC LIMIT 1",(uid,now,now)).fetchone()
        if not grant:raise HTTPException(403,'O envio exige plano pago ativo.')
        used=db.execute('SELECT coalesce(sum(delta),0) FROM essay_credit_events WHERE grant_id=?',(grant['order_id'],)).fetchone()[0]
        return grant,max(0,grant['essay_credits']-used)
    def submit(self,uid,key,theme,text):
        self.guard();now=int(self.clock())
        with self.store.connect(write=True) as db:
            old=db.execute('SELECT * FROM real_essay_jobs WHERE user_id=? AND request_key=?',(uid,key)).fetchone()
            if old:
                if old['theme']!=theme or old['text']!=text:raise HTTPException(409,'Identificador já usado para outro texto.')
                return dict(id=old['id'],status=old['status'])
            grant,remaining=self.balance(db,uid)
            if not remaining:raise HTTPException(409,'Créditos de correção esgotados neste período.')
            if db.execute("SELECT 1 FROM real_essay_jobs WHERE user_id=? AND status IN ('pending','processing')",(uid,)).fetchone():
                raise HTTPException(409,'Aguarde sua correção pendente antes de enviar outra.')
            jid=str(uuid.uuid4())
            db.execute("INSERT INTO real_essay_jobs(id,user_id,grant_id,request_key,theme,text,status,created_at,available_at,model,rubric_version,prompt_version) VALUES(?,?,?,?,?,?,'pending',?,?,?,?,?)",(jid,uid,grant['order_id'],key,theme,text,now,now,self.model,RUBRIC,PROMPT))
            db.execute("INSERT INTO essay_credit_events VALUES(?,?,'reserve',1,?)",(jid,grant['order_id'],now))
        return dict(id=jid,status='pending')
    def own(self,db,uid,jid):
        row=db.execute('SELECT * FROM real_essay_jobs WHERE id=? AND user_id=?',(jid,uid)).fetchone()
        if not row:raise HTTPException(404,'Correção não encontrada.')
        return row
    def detail(self,uid,jid):
        self.guard()
        with self.store.connect() as db:row=self.own(db,uid,jid)
        return dict(id=jid,theme=row['theme'],text=row['text'],status=row['status'],created_at=row['created_at'],
            result=json.loads(row['result']) if row['result'] else None,error=row['error'],model=row['model'],rubric_version=row['rubric_version'])
    def history(self,uid):
        self.guard()
        with self.store.connect() as db:
            rows=[dict(r) for r in db.execute('SELECT id,theme,status,created_at,model,rubric_version FROM real_essay_jobs WHERE user_id=? ORDER BY created_at DESC,id LIMIT 100',(uid,))]
            try:_,remaining=self.balance(db,uid)
            except HTTPException:remaining=0
        return dict(items=rows,remaining=remaining,notice='Correção automatizada experimental. Cada conclusão consome 1 crédito; falha definitiva libera a reserva. Sem revisão humana.')
    def evolution(self,uid):
        self.guard()
        with self.store.connect() as db:
            if not entitlement(db,uid,self.clock())['active']:raise HTTPException(403,'Evolução exige plano pago ativo.')
            rows=db.execute("SELECT id,theme,created_at,model,rubric_version,prompt_version,result FROM real_essay_jobs WHERE user_id=? AND status='completed' ORDER BY created_at DESC,id LIMIT 100",(uid,)).fetchall()
        groups={}
        for row in reversed(rows):
            result=json.loads(row['result']);key=(result.get('provider_model',row['model']),row['rubric_version'],row['prompt_version'])
            groups.setdefault(key,[]).append(dict(id=row['id'],theme=row['theme'],created_at=row['created_at'],scores={str(c['id']):c['score'] for c in result['competencies']}))
        return dict(groups=[dict(model=k[0],rubric_version=k[1],prompt_version=k[2],items=v) for k,v in groups.items()],notice='Até 100 resultados reais recentes. Versões diferentes são separadas; variação de estimativa não comprova evolução pedagógica. Demonstrações não entram nesta análise.')

class EssayWorker:
    def __init__(self,store,evaluator,clock=time.time,daily_limit=20,lease_seconds=120):
        if not 1<=daily_limit<=100 or lease_seconds<90:raise ValueError('Limites de execução inválidos.')
        self.store,self.evaluator,self.clock,self.daily_limit,self.lease=store,evaluator,clock,daily_limit,lease_seconds
    def active(self,db,job,now):
        return db.execute("SELECT 1 FROM access_grants WHERE order_id=? AND user_id=? AND status='active' AND starts_at<=? AND ends_at>?",(job['grant_id'],job['user_id'],now,now)).fetchone()
    def fail(self,db,job,code,now):
        db.execute("UPDATE real_essay_jobs SET status='failed',error=?,lease_token=NULL,lease_until=NULL WHERE id=?",(code,job['id']))
        db.execute("INSERT OR IGNORE INTO essay_credit_events VALUES(?,?,'release',-1,?)",(job['id'],job['grant_id'],now))
    def claim(self):
        now=int(self.clock())
        with self.store.connect(write=True) as db:
            # Single global in-flight call per pilot database, even across worker processes.
            if db.execute("SELECT 1 FROM real_essay_jobs WHERE status='processing' AND lease_until>?",(now,)).fetchone():return None
            job=db.execute("SELECT * FROM real_essay_jobs WHERE (status='pending' AND available_at<=?) OR (status='processing' AND lease_until<=?) ORDER BY created_at,id LIMIT 1",(now,now)).fetchone()
            if not job:return None
            job=dict(job)
            if job['attempts']>=3 or not self.active(db,job,now):
                self.fail(db,job,'retry_limit' if job['attempts']>=3 else 'access_expired',now);return None
            if job['model']!=self.evaluator.model or job['rubric_version']!=RUBRIC or job['prompt_version']!=PROMPT:
                self.fail(db,job,'evaluator_version_mismatch',now);return None
            if db.execute('SELECT count(*) FROM essay_provider_calls WHERE created_at>=?',(now-now%86400,)).fetchone()[0]>=self.daily_limit:return None
            token=str(uuid.uuid4())
            db.execute("UPDATE real_essay_jobs SET status='processing',attempts=attempts+1,lease_token=?,lease_until=? WHERE id=?",(token,now+self.lease,job['id']))
            db.execute('INSERT INTO essay_provider_calls(job_id,created_at) VALUES(?,?)',(job['id'],now))
            job.update(lease_token=token,attempts=job['attempts']+1)
        return job
    def run_once(self):
        job=self.claim()
        if not job:return False
        result=None;failure=None
        try:
            # No database transaction is held while contacting the provider.
            received=self.evaluator.evaluate(job['theme'],job['text'])
            # Validate locally again, including every literal quote and competency.
            result=canonical(dict(competencies=received['competencies'],annotations=[{k:a[k] for k in ('competency','quote','guidance')} for a in received['annotations']]),job['text'])
            resolved=received.get('provider_model',job['model'])
            if not isinstance(resolved,str) or not 1<=len(resolved)<=200:raise ProviderFailure('invalid_output')
            result['provider_model']=resolved
            usage=received.get('usage',{})
            result['usage']={k:usage[k] for k in ('input_tokens','output_tokens','total_tokens') if isinstance(usage.get(k),int) and not isinstance(usage[k],bool) and 0<=usage[k]<=1_000_000}
        except ProviderFailure as exc:failure=exc
        except Exception:failure=ProviderFailure('invalid_output')
        now=int(self.clock())
        with self.store.connect(write=True) as db:
            current=db.execute("SELECT * FROM real_essay_jobs WHERE id=? AND status='processing' AND lease_token=? AND lease_until>?",(job['id'],job['lease_token'],now)).fetchone()
            if not current:return True # Fencing: stale workers cannot settle or release credits.
            if not self.active(db,job,now):self.fail(db,job,'access_expired',now)
            elif failure:
                if failure.retryable and job['attempts']<3:
                    db.execute("UPDATE real_essay_jobs SET status='pending',available_at=?,lease_token=NULL,lease_until=NULL,error=? WHERE id=?",(now+60*job['attempts'],failure.code,job['id']))
                else:self.fail(db,job,failure.code,now)
            else:
                db.execute("UPDATE real_essay_jobs SET status='completed',result=?,error=NULL,lease_token=NULL,lease_until=NULL WHERE id=?",(json.dumps(result,ensure_ascii=False),job['id']))
                db.execute("INSERT OR IGNORE INTO essay_credit_events VALUES(?,?,'consume',0,?)",(job['id'],job['grant_id'],now))
        return True
