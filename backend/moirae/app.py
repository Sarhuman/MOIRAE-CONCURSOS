import os
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .store import Store
from .security import digest, hasher, verify
from .service import Practice
from .middleware import BodyLimit
from .exams import Exams

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


def create_app(db_path=None,origin=None,secure=None):
    origin=origin or os.getenv('MOIRAE_ORIGIN','http://127.0.0.1:8000')
    secure=(os.getenv('MOIRAE_SECURE_COOKIE','true').lower()=='true') if secure is None else secure
    if not origin.startswith(('http://127.0.0.1:','http://localhost:','http://terminal.local:','https://')):
        raise ValueError('Use origem HTTPS ou localhost.')
    if origin.startswith('https://') and not secure:
        raise ValueError('HTTPS exige cookie Secure.')
    store=Store(db_path or os.getenv('MOIRAE_DB',str(ROOT/'var'/'moirae.sqlite3')))
    practice=Practice(store)
    exams=Exams(store)
    app=FastAPI(title='MOIRAE — piloto',docs_url=None,redoc_url=None,openapi_url=None)
    app.state.store=store
    app.state.practice=practice
    app.state.exams=exams
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
            if request.headers.get('origin')!=origin:
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
            size=request.headers.get('content-length','')
            if not size.isdigit() or int(size)>16384:
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
            if request.method!='GET' and not secrets.compare_digest(request.headers.get('x-csrf-token',''),session['csrf']):
                raise HTTPException(403,'Reabra a página e tente novamente.')
            return dict(session)

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
    def register(body:Credentials,request:Request,response:Response):
        rate(request,body.email)
        encoded=hasher.hash(body.password)
        uid=str(uuid.uuid4())
        try:
            with store.connect(write=True) as db:
                db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,body.email,encoded,int(time.time())))
        except sqlite3.IntegrityError:
            raise HTTPException(409,'Não foi possível criar a conta com esses dados. Se já tem conta, tente entrar.')
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
        return dict(plan='free',csrf=auth['csrf'])

    @app.post('/api/auth/logout')
    def logout(response:Response,request:Request,auth=Depends(user)):
        with store.connect(write=True) as db:db.execute('DELETE FROM auth_sessions WHERE token_hash=?',(auth['token_hash'],))
        response.delete_cookie(cookie,path='/',secure=secure,httponly=True,samesite='strict')
        return {'ok':True}

    @app.get('/api/practice/current')
    def current(auth=Depends(user)):return practice.current(auth['user_id'])

    @app.post('/api/practice/start')
    def start(auth=Depends(user)):return practice.start(auth['user_id'])

    @app.post('/api/practice/answer')
    def answer(body:Answer,auth=Depends(user)):
        return practice.answer(auth['user_id'],str(body.session_id),body.question_id,body.choice,str(body.key))

    @app.get('/api/exams/current')
    def exam_current(auth=Depends(user)):return exams.current(auth['user_id'])

    @app.post('/api/exams/start')
    def exam_start(body:ExamStart,auth=Depends(user)):
        return exams.start(auth['user_id'],body.day,str(body.key))

    @app.post('/api/exams/{exam_id}/item')
    def exam_item(exam_id:uuid.UUID,body:ExamItem,auth=Depends(user)):
        return exams.save_item(auth['user_id'],str(exam_id),body.question_id,body.choice,body.flagged,body.revision)

    @app.post('/api/exams/{exam_id}/essay')
    def exam_essay(exam_id:uuid.UUID,body:EssayDraft,auth=Depends(user)):
        return exams.save_essay(auth['user_id'],str(exam_id),body.text,body.revision)

    @app.post('/api/exams/{exam_id}/finish')
    def exam_finish(exam_id:uuid.UUID,auth=Depends(user)):
        return exams.finish(auth['user_id'],str(exam_id))

    @app.get('/api/dashboard')
    def dashboard(auth=Depends(user)):
        raise HTTPException(403,'O painel de desempenho não faz parte do plano Free. Planos pagos ainda indisponíveis.')

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
