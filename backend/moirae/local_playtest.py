"""Isolated local test database. Never grants access in an existing database."""
import argparse
import getpass
import os
import re
import time
import uuid
from pathlib import Path
from .store import Store
from .security import hasher
from .accounts import POLICY_VERSION
from .plans import PLANS
from .sandbox_wallet import SandboxWallet

def create_playtest(path,email,password,plan='avancado',wallet_credits=0):
    if type(wallet_credits) is not int or not 0<=wallet_credits<=10000:raise ValueError('Quantidade de créditos de teste inválida.')
    email=email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254:raise ValueError('E-mail inválido.')
    if not 12<=len(password)<=128:raise ValueError('Use senha de 12 a 128 caracteres.')
    if plan not in PLANS:raise ValueError('Plano inválido.')
    target=Path(path).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    # Atomic no-clobber: even an empty existing database must never be reused.
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    store=Store(str(target));uid=str(uuid.uuid4());oid=str(uuid.uuid4());now=int(time.time());p=PLANS[plan]
    with store.connect(write=True) as db:
        db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,email,hasher.hash(password),now))
        db.execute('INSERT INTO user_profiles VALUES(?,1,?,?,1)',(uid,POLICY_VERSION,now))
        db.execute("INSERT INTO billing_orders(id,user_id,plan_id,amount_cents,status,created_at,request_key,essay_credits,access_days,catalog_version) VALUES(?,?,?,0,'local_test',?,?,?,?,?)",(oid,uid,plan,now,oid,p['essay_credits'],30,p['catalog_version']))
        db.execute("INSERT INTO access_grants VALUES(?,?,?,?,?,'active',?)",(oid,uid,plan,now,now+30*86400,p['essay_credits']))
    if wallet_credits:
        SandboxWallet(store,enabled=True).grant(uid,'local-playtest:'+oid,wallet_credits,now+30*86400)
    return dict(database=str(target),email=email,plan=plan)

def main():
    parser=argparse.ArgumentParser(description='Cria banco NOVO e isolado para teste local; não simula pagamento real.')
    parser.add_argument('--database',required=True);parser.add_argument('--email',default='henrique@example.test');parser.add_argument('--plan',choices=tuple(PLANS),default='avancado');parser.add_argument('--wallet-credits',type=int,default=0);args=parser.parse_args()
    for name in ('MOIRAE_ESSAY_AI','MOIRAE_ESSAY_AI_REVIEWED','MOIRAE_MP_SANDBOX'):
        if os.getenv(name,'false').lower()=='true':parser.error('Desative integrações externas antes de criar o ambiente local.')
    if args.wallet_credits and os.getenv('MOIRAE_COMMERCE_SANDBOX','false').lower()!='true':parser.error('Ative MOIRAE_COMMERCE_SANDBOX para preparar créditos de teste.')
    password=getpass.getpass('Crie uma senha de teste (mínimo 12 caracteres): ')
    if password!=getpass.getpass('Repita a senha: '):parser.error('As senhas não coincidem.')
    try:result=create_playtest(args.database,args.email,password,args.plan,args.wallet_credits)
    except FileExistsError:parser.error('O arquivo já existe; escolha outro banco. Nenhum dado foi sobrescrito.')
    except ValueError as exc:parser.error(str(exc))
    print('Banco isolado criado. E-mail:',result['email'],'Plano:',result['plan'])
    print('Use o mesmo arquivo em MOIRAE_DB. Não há integração externa ou pagamento neste preparo.')
if __name__=='__main__':main()
