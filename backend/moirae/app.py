import os
import json
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .store import Store
from .security import digest, hasher, verify
from .service import Practice
from .middleware import BodyLimit
from .exams import Exams
from .accounts import Accounts
from .mail import LocalMail, MailUnavailable
from .billing import Billing
from .mercadopago import MercadoPagoSandbox, verify_signature
from .plans import entitlement
from .catalog import BY_ID
from .essays import Essays
from .review import Review
from .planner import Planner
from .essay_jobs import EssayJobs
from .commercial import catalog as commercial_catalog,quote as commercial_quote

ROOT=Path(__file__).resolve().parents[2]


class Credentials(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email: str=Field(min_length=3,max_length=254)
    password: str=Field(min_length=12,max_length=128)

    @field_validator('email')
    @classmethod
    def normalize_email(cls,value):
        value=value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):
            raise ValueError('Informe um e-mail válido.')
        return value


class Registration(Credentials):
    accept_terms: Literal[True]
    adult_pilot: Literal[True]


class EmailOnly(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email: str=Field(min_length=3,max_length=254)
    @field_validator('email')
    @classmethod
    def normalize(cls,value):return Credentials.normalize_email(value)


class TokenInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    token: str=Field(min_length=32,max_length=128)


class ResetInput(TokenInput):
    password: str=Field(min_length=12,max_length=128)


class Reauthenticate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    password: str=Field(min_length=12,max_length=128)


class DeleteAccount(Reauthenticate):
    confirmation: Literal['EXCLUIR']


class AcceptPolicy(Reauthenticate):
    accept_terms: Literal[True]
    adult_pilot: Literal[True]


class CheckoutInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    plan: Literal['essencial','avancado']
    key: uuid.UUID


class Answer(BaseModel):
    model_config=ConfigDict(extra='forbid')
    session_id: uuid.UUID
    question_id: str=Field(max_length=40)
    choice: str=Field(pattern='^[a-e]$')
    key: uuid.UUID


class ExamStart(BaseModel):
    model_config=ConfigDict(extra='forbid')
    day: Literal[1,2]
    key: uuid.UUID


class ExamItem(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question_id: str=Field(max_length=40)
    choice: str | None=Field(default=None,pattern='^[a-e]$')
    flagged: bool=False
    revision: int=Field(ge=0)


class EssayDraft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text: str=Field(max_length=4000)
    revision: int=Field(ge=0)


class EssaySubmission(BaseModel):
    model_config=ConfigDict(extra='forbid')
    key: uuid.UUID
    theme: str=Field(min_length=3,max_length=200)
    text: str=Field(min_length=100,max_length=4000)

    @field_validator('theme','text')
    @classmethod
    def meaningful(cls,value,info):
        if len(value.strip()) < (100 if info.field_name=='text' else 3):
            raise ValueError('Preencha o texto.')
        try:value.encode('utf-16-le')
        except UnicodeEncodeError:raise ValueError('Texto inválido.')
        return value

class PlannedSessionInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    minutes: Literal[15,30,60]

class FavoriteInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    enabled: bool

class RealEssaySubmission(EssaySubmission):
    accept_external: bool=Field(strict=True)
    @field_validator('accept_external')
    @classmethod
    def accept_processing(cls,value):
        if not value:raise ValueError('Confirme o processamento externo do texto.')
        return value

class EssayRewrite(BaseModel):
    model_config=ConfigDict(extra='forbid')
    key: uuid.UUID
    annotation_id: str=Field(min_length=1,max_length=40)
    text: str=Field(min_length=20,max_length=1200)


def create_app(db_path=None,origin=None,secure=None,mailer=None,billing_provider=None,billing_collector=None,billing_secret=None,essay_demo=None):
    origin=origin or os.getenv('MOIRAE_ORIGIN','http://127.0.0.1:8000')
    secure=(os.getenv('MOIRAE_SECURE_COOKIE','true').lower()=='true') if secure is None else secure
    if not origin.startswith(('http://127.0.0.1:','http://localhost:','http://terminal.local:','https://')):
        raise ValueError('Use origem HTTPS ou localhost.')
    if origin.startswith('https://') and not secure:
        raise ValueError('HTTPS exige cookie Secure.')
    store=Store(db_path or os.getenv('MOIRAE_DB',str(ROOT/'var'/'moirae.sqlite3')))
    mailer=mailer or (LocalMail(Path(store.path).parent/'mail-outbox') if not secure else MailUnavailable())
    accounts=Accounts(store,mailer,origin)
    if os.getenv('MOIRAE_MP_SANDBOX','false').lower()=='true' and billing_provider is None:
        token=os.getenv('MOIRAE_MP_ACCESS_TOKEN','')
        billing_collector=os.getenv('MOIRAE_MP_COLLECTOR_ID','')
        billing_secret=os.getenv('MOIRAE_MP_WEBHOOK_SECRET','')
        if not token or not billing_collector.isdigit() or len(billing_secret)<32 or not origin.startswith('https://'):
            raise ValueError('Configuração sandbox incompleta; verifique credenciais e origem HTTPS.')
        billing_provider=MercadoPagoSandbox(token)
    billing=Billing(store,billing_provider,billing_collector,billing_secret,origin)
    essays=Essays(store, enabled=(os.getenv('MOIRAE_ESSAY_DEMO','false').lower()=='true') if essay_demo is None else essay_demo)
    real_essays=EssayJobs(store,enabled=os.getenv('MOIRAE_ESSAY_AI','false').lower()=='true' and os.getenv('MOIRAE_ESSAY_AI_REVIEWED','false').lower()=='true',model=os.getenv('MOIRAE_ESSAY_MODEL',''))
    practice=Practice(store)
    exams=Exams(store)
    app=FastAPI(title='MOIRAE — piloto',docs_url=None,redoc_url=None,openapi_url=None)
    app.state.store=store
    app.state.practice=practice
    app.state.exams=exams
    app.state.accounts=accounts
    app.state.mailer=mailer
    app.state.billing=billing
    app.state.essays=essays
    app.state.real_essays=real_essays
    cookie='__Host-moirae' if secure else 'moirae_local'

    @app.exception_handler(sqlite3.OperationalError)
    async def database_unavailable(request, error):
        return JSONResponse({'detail':'Não foi possível acessar seus dados agora. Tente novamente.'},status_code=503)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, error):
        return JSONResponse({'detail':'Confira os campos e os limites informados na tela.'},status_code=422)

    @app.middleware('http')
    async def guard(request:Request,call_next):
        # Navegador e API são servidos pela mesma origem; sem CORS permissivo.
        if request.method in ('POST','PUT','PATCH','DELETE'):
            webhook=request.url.path=='/api/billing/webhook'
            if not webhook and request.headers.get('origin')!=origin:
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
            size=request.headers.get('content-length','')
            if (not size.isdigit() and not (webhook and not size)) or (size.isdigit() and int(size)>16384):
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail':'Envio inválido ou grande demais.'},status_code=413)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    def rate(request,email):
        now=int(time.time());window=now//60
        buckets=[('ip:'+digest(request.client.host if request.client else 'unknown'),20),('account:'+digest(email),10)]
        with store.connect(write=True) as db:
            db.execute('DELETE FROM rate_limits WHERE window<?',(window-2,))
            for bucket,limit in buckets:
                count=db.execute('SELECT count FROM rate_limits WHERE bucket=? AND window=?',(bucket,window)).fetchone()
                if count and count[0]>=limit:
                    raise HTTPException(429,'Muitas tentativas. Aguarde um minuto.')
            for bucket,limit in buckets:
                db.execute('INSERT INTO rate_limits VALUES(?,?,1) ON CONFLICT(bucket,window) DO UPDATE SET count=count+1',(bucket,window))

    def user(request:Request):
        raw=request.cookies.get(cookie,'')
        with store.connect() as db:
            session=db.execute('SELECT * FROM auth_sessions WHERE token_hash=? AND expires_at>?',(digest(raw),int(time.time()))).fetchone()
            if not session:
                raise HTTPException(401,'Entre na sua conta para continuar.')
            if request.method!='GET' and not secrets.compare_digest(request.headers.get('x-csrf-token','').encode(),session['csrf'].encode()):
                raise HTTPException(403,'Reabra a página e tente novamente.')
            return dict(session)

    def student(auth=Depends(user)):
        accounts.require_student(auth['user_id'])
        return auth

    def issue(response,user_id):
        raw=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        with store.connect(write=True) as db:
            db.execute('DELETE FROM auth_sessions WHERE expires_at<=?',(int(time.time()),))
            db.execute('INSERT INTO auth_sessions VALUES(?,?,?,?)',(digest(raw),user_id,csrf,int(time.time())+28800))
        response.set_cookie(cookie,raw,httponly=True,secure=secure,samesite='strict',max_age=28800,path='/')
        return dict(plan='free',csrf=csrf)

    @app.get('/api/health')
    def health():
        with store.connect() as db:db.execute('SELECT 1')
        return {'status':'ok','stage':'local-pilot'}

    @app.post('/api/auth/register',status_code=201)
    def register(body:Registration,request:Request,response:Response):
        rate(request,body.email)
        if isinstance(mailer,MailUnavailable):
            raise HTTPException(503,'Cadastro público indisponível: entrega de e-mails não configurada.')
        encoded=hasher.hash(body.password)
        uid=str(uuid.uuid4())
        try:
            with store.connect(write=True) as db:
                db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,body.email,encoded,int(time.time())))
        except sqlite3.IntegrityError:
            raise HTTPException(409,'Não foi possível criar a conta com esses dados. Se já tem conta, tente entrar.')
        accounts.accept(uid)
        accounts.issue(uid,'verify')
        return issue(response,uid)

    @app.post('/api/auth/login')
    def login(body:Credentials,request:Request,response:Response):
        rate(request,body.email)
        with store.connect() as db:row=db.execute('SELECT * FROM users WHERE email=?',(body.email,)).fetchone()
        if not verify(row['password_hash'] if row else None,body.password):
            raise HTTPException(401,'E-mail ou senha incorretos.')
        return issue(response,row['id'])

    @app.get('/api/auth/me')
    def me(auth=Depends(user)):
        with store.connect() as db:access=entitlement(db,auth['user_id'])
        return dict(plan=access['plan'],csrf=auth['csrf'],**accounts.profile(auth['user_id']))

    @app.post('/api/auth/logout')
    def logout(response:Response,request:Request,auth=Depends(user)):
        with store.connect(write=True) as db:db.execute('DELETE FROM auth_sessions WHERE token_hash=?',(auth['token_hash'],))
        response.delete_cookie(cookie,path='/',secure=secure,httponly=True,samesite='strict')
        return {'ok':True}

    @app.post('/api/auth/verify-email')
    def verify_email(body:TokenInput):return accounts.consume(body.token,'verify')

    @app.post('/api/auth/request-reset')
    def request_reset(body:EmailOnly,request:Request):
        rate(request,body.email)
        return accounts.request_reset(body.email)

    @app.post('/api/auth/reset-password')
    def reset_password(body:ResetInput,request:Request):
        rate(request,'reset:'+digest(body.token))
        return accounts.consume(body.token,'reset',body.password)

    @app.post('/api/account/resend-verification')
    def resend(request:Request,auth=Depends(user)):
        email=accounts.profile(auth['user_id'])['email'];rate(request,email)
        accounts.issue(auth['user_id'],'verify')
        return {'message':'Novo link preparado. No piloto local, consulte a caixa de saída do servidor.'}

    @app.post('/api/account/accept-policy')
    def accept_policy(body:AcceptPolicy,request:Request,auth=Depends(user)):
        rate(request,'account:'+auth['user_id'])
        with store.connect() as db:accounts.reauthenticate(db,auth['user_id'],body.password)
        accounts.accept(auth['user_id'])
        return {'ok':True}

    @app.post('/api/account/export')
    def export(body:Reauthenticate,request:Request,auth=Depends(user)):
        rate(request,'account:'+auth['user_id'])
        data=accounts.export(auth['user_id'],body.password)
        return Response(json.dumps(data,ensure_ascii=False),media_type='application/json',headers={'Content-Disposition':'attachment; filename="moirae-dados.json"'})

    @app.post('/api/account/delete')
    def delete_account(body:DeleteAccount,request:Request,response:Response,auth=Depends(user)):
        rate(request,'account:'+auth['user_id'])
        result=accounts.erase(auth['user_id'],body.password)
        response.delete_cookie(cookie,path='/',secure=secure,httponly=True,samesite='strict')
        return result

    @app.get('/api/practice/current')
    def current(auth=Depends(student)):return practice.current(auth['user_id'])

    @app.post('/api/practice/start')
    def start(auth=Depends(student)):return practice.start(auth['user_id'])

    @app.post('/api/practice/answer')
    def answer(body:Answer,auth=Depends(student)):
        return practice.answer(auth['user_id'],str(body.session_id),body.question_id,body.choice,str(body.key))

    @app.get('/api/exams/current')
    def exam_current(auth=Depends(student)):return exams.current(auth['user_id'])

    @app.post('/api/exams/start')
    def exam_start(body:ExamStart,auth=Depends(student)):
        return exams.start(auth['user_id'],body.day,str(body.key))

    @app.post('/api/exams/{exam_id}/item')
    def exam_item(exam_id:uuid.UUID,body:ExamItem,auth=Depends(student)):
        return exams.save_item(auth['user_id'],str(exam_id),body.question_id,body.choice,body.flagged,body.revision)

    @app.post('/api/exams/{exam_id}/essay')
    def exam_essay(exam_id:uuid.UUID,body:EssayDraft,auth=Depends(student)):
        return exams.save_essay(auth['user_id'],str(exam_id),body.text,body.revision)

    @app.post('/api/exams/{exam_id}/finish')
    def exam_finish(exam_id:uuid.UUID,auth=Depends(student)):
        return exams.finish(auth['user_id'],str(exam_id))

    @app.get('/api/commercial/catalog')
    def commercial_products():return commercial_catalog()

    @app.get('/api/commercial/quote')
    def commercial_preview(product:str,cycles:int=1,installments:int=1):return commercial_quote(product,cycles,installments)

    @app.get('/biblioteca')
    def library_page():return FileResponse(ROOT/'web'/'biblioteca.html')

    @app.get('/api/billing/plans')
    def plans():return billing.catalog()

    @app.get('/api/billing/current')
    def billing_current(auth=Depends(user)):return billing.current(auth['user_id'])

    @app.post('/api/billing/checkout')
    def checkout(body:CheckoutInput,request:Request,auth=Depends(student)):
        rate(request,'checkout:'+auth['user_id'])
        return billing.start(auth['user_id'],body.plan,str(body.key))

    @app.post('/api/billing/orders/{order_id}/refund-request')
    def refund_request(order_id:uuid.UUID,body:Reauthenticate,request:Request,auth=Depends(user)):
        rate(request,'account:'+auth['user_id'])
        with store.connect() as db:accounts.reauthenticate(db,auth['user_id'],body.password)
        return billing.request_refund(auth['user_id'],str(order_id))

    @app.post('/api/billing/webhook')
    async def webhook(request:Request):
        if not billing.ready():raise HTTPException(503,'Integração indisponível.')
        ids=request.query_params.getlist('data.id')
        if len(ids)!=1:raise HTTPException(400,'Identificador de pagamento inválido.')
        payment_id=ids[0]
        verify_signature(payment_id,request.headers.get('x-request-id',''),request.headers.get('x-signature',''),billing.secret,billing.clock())
        try:body=await request.json()
        except ValueError:raise HTTPException(400,'Notificação inválida.')
        if not isinstance(body,dict):raise HTTPException(400,'Notificação inválida.')
        if body.get('type')!='payment':return {'ok':True,'ignored':'unsupported_type'}
        if not isinstance(body.get('data'),dict) or str(body['data'].get('id'))!=payment_id:raise HTTPException(400,'Identificadores divergentes.')
        # SDK HTTP síncrono em worker, sem bloquear o event loop do servidor.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(billing.reconcile,payment_id)

    @app.post('/api/practice/enem-2025/start')
    def official_practice_start(request:Request,auth=Depends(student)):
        rate(request,'practice:'+auth['user_id'])
        return practice.start(auth['user_id'],official=True)

    @app.post('/api/practice/enem-2025/batch-2/start')
    def official_batch_two_start(request:Request,auth=Depends(student)):
        rate(request,'practice:'+auth['user_id'])
        return practice.start(auth['user_id'],official=2)

    @app.post('/api/practice/enem-2025/batch-3/start')
    def official_batch_three_start(request:Request,auth=Depends(student)):
        rate(request,'practice:'+auth['user_id'])
        return practice.start(auth['user_id'],official=3)

    @app.get('/acervo-enem')
    def archive_page():return FileResponse(ROOT/'web'/'enem-archive.html')

    @app.get('/api/enem-archive')
    def archive_index():return FileResponse(ROOT/'data'/'inep'/'archive-index.json',media_type='application/json')

    @app.get('/acervo-enem/{year}/{name}')
    def archive_pdf(year:int,name:str):
        import json
        rows=json.loads((ROOT/'data'/'inep'/'archive-index.json').read_text(encoding='utf-8'))
        valid=any(row['year']==year and any(f['name']==name and f['status']=='downloaded' for f in row['files']) for row in rows)
        if not valid or Path(name).name!=name:raise HTTPException(404,'Arquivo não encontrado.')
        path=ROOT/'var'/'inep'/'archive'/str(year)/name
        if not path.is_file():raise HTTPException(404,'PDF não instalado nesta instância. Use a fonte oficial.')
        return FileResponse(path,media_type='application/pdf',filename=name)

    @app.get('/diagnostico')
    def diagnostic_page():return FileResponse(ROOT/'web'/'diagnostic.html')

    @app.post('/api/diagnostic/start')
    def diagnostic_start(request:Request,auth=Depends(student)):
        rate(request,'diagnostic:'+auth['user_id'])
        return practice.start(auth['user_id'],diagnostic=True)

    @app.get('/api/diagnostic')
    def diagnostic_result(auth=Depends(student)):
        from .diagnostic import result
        return result(store,auth['user_id'])

    @app.get('/api/planner')
    def planner_preview(minutes:int=Query(default=30),auth=Depends(student)):
        if minutes not in (15,30,60):raise HTTPException(422,'Escolha 15, 30 ou 60 minutos.')
        return Planner(store).preview(auth['user_id'],minutes)

    @app.post('/api/planner/start')
    def planner_start(body:PlannedSessionInput,request:Request,auth=Depends(student)):
        rate(request,'planner:'+auth['user_id'])
        return practice.start(auth['user_id'],body.minutes)

    @app.get('/api/review')
    def review_list(view:Literal['errors','favorites','all']='errors',auth=Depends(student)):
        return Review(store).listing(auth['user_id'],view)

    @app.post('/api/review/{question_id}/favorite')
    def review_favorite(question_id:str,body:FavoriteInput,request:Request,auth=Depends(student)):
        rate(request,'review:'+auth['user_id'])
        return Review(store).favorite(auth['user_id'],question_id,body.enabled)

    @app.get('/caderno')
    def review_page():return FileResponse(ROOT/'web'/'review.html')

    @app.get('/api/dashboard')
    def dashboard(auth=Depends(student)):
        with store.connect(write=True) as db:
            access=entitlement(db,auth['user_id'])
            if not access['active']:raise HTTPException(403,'O painel de desempenho exige plano pago ativo. Checkout de produção ainda indisponível.')
            exams.expire(db,auth['user_id'])
            rows=db.execute('SELECT question_id,correct,day FROM attempts WHERE user_id=?',(auth['user_id'],)).fetchall()
            areas={};correct=0
            for row in rows:
                area=BY_ID[row['question_id']].area if row['question_id'] in BY_ID else 'Não classificado'
                areas.setdefault(area,{'answered':0,'correct':0});areas[area]['answered']+=1;areas[area]['correct']+=row['correct'];correct+=row['correct']
            recent=[dict(r) for r in db.execute('SELECT question_id,choice,correct,day FROM attempts WHERE user_id=? ORDER BY created_at DESC,rowid DESC LIMIT 20',(auth['user_id'],))]
            completed=db.execute("SELECT count(*) FROM mock_exams WHERE user_id=? AND status!='active'",(auth['user_id'],)).fetchone()[0]
        return dict(access=access,answered=len(rows),correct=correct,accuracy=round(100*correct/len(rows),1) if rows else None,areas=areas,recent_attempts=recent,completed_mock_exams=completed,notice='Resultados do catálogo introdutório de teste; não equivalem a nota oficial ou TRI.')

    @app.get('/planos')
    def plans_page():return FileResponse(ROOT/'web'/'plans.html')

    @app.get('/redacoes-ia')
    def real_essays_page():return FileResponse(ROOT/'web'/'real-essays.html')

    @app.get('/api/essay-evaluations')
    def real_history(auth=Depends(student)):return real_essays.history(auth['user_id'])

    @app.get('/api/essay-evaluations/evolution')
    def real_evolution(auth=Depends(student)):return real_essays.evolution(auth['user_id'])

    @app.post('/api/essay-evaluations',status_code=202)
    def real_submit(body:RealEssaySubmission,request:Request,auth=Depends(student)):
        rate(request,'real-essay:'+auth['user_id'])
        return real_essays.submit(auth['user_id'],str(body.key),body.theme,body.text)

    @app.get('/api/essay-evaluations/{job_id}')
    def real_detail(job_id:uuid.UUID,auth=Depends(student)):return real_essays.detail(auth['user_id'],str(job_id))

    @app.get('/api/essays')
    def essay_history(auth=Depends(student)):return essays.history(auth['user_id'])

    @app.post('/api/essays',status_code=201)
    def essay_submit(body:EssaySubmission,request:Request,auth=Depends(student)):
        rate(request,'essay:'+auth['user_id'])
        return essays.submit(auth['user_id'],str(body.key),body.theme,body.text)

    @app.get('/api/essays/{essay_id}')
    def essay_detail(essay_id:uuid.UUID,auth=Depends(student)):
        return essays.detail(auth['user_id'],str(essay_id))

    @app.post('/api/essays/{essay_id}/process')
    def essay_process(essay_id:uuid.UUID,request:Request,auth=Depends(student)):
        rate(request,'essay:'+auth['user_id'])
        return essays.process(auth['user_id'],str(essay_id))

    @app.post('/api/essays/{essay_id}/rewrites',status_code=201)
    def essay_rewrite(essay_id:uuid.UUID,body:EssayRewrite,request:Request,auth=Depends(student)):
        rate(request,'essay:'+auth['user_id'])
        return essays.rewrite(auth['user_id'],str(essay_id),str(body.key),body.annotation_id,body.text)

    @app.get('/redacoes')
    def essays_page():return FileResponse(ROOT/'web'/'essays.html')

    @app.get('/painel')
    def dashboard_page():return FileResponse(ROOT/'web'/'dashboard.html')

    @app.get('/conta')
    @app.get('/verificar-email')
    @app.get('/recuperar-senha')
    def account_page():return FileResponse(ROOT/'web'/'account.html')

    @app.get('/simulados')
    def mocks():return FileResponse(ROOT/'web'/'exam.html')

    @app.get('/estudar')
    def study():return FileResponse(ROOT/'web'/'study.html')

    @app.get('/')
    def landing():return FileResponse(ROOT/'web'/'index.html')

    app.mount('/assets',StaticFiles(directory=ROOT/'web'),name='assets')
    app.mount('/',StaticFiles(directory=ROOT/'web',html=True),name='public')
    app.add_middleware(BodyLimit)
    return app
