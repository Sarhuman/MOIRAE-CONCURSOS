import secrets
import time
from fastapi import HTTPException
from .security import digest,hasher,verify

POLICY_VERSION='pilot-2026-11-03'
GENERIC_RESET='Se houver uma conta com esse e-mail, as instruções de recuperação serão preparadas.'


class Accounts:
    def __init__(self,store,mailer,origin,clock=time.time):self.store,self.mailer,self.origin,self.clock=store,mailer,origin,clock

    def profile(self,user_id):
        with self.store.connect() as db:
            row=db.execute('SELECT email,created_at FROM users WHERE id=?',(user_id,)).fetchone()
            if not row:raise HTTPException(401,'Entre novamente para continuar.')
            profile=db.execute('SELECT * FROM user_profiles WHERE user_id=?',(user_id,)).fetchone()
            return dict(email=row['email'],email_verified=bool(profile and profile['email_verified']),
                        policy_accepted=bool(profile and profile['policy_version']==POLICY_VERSION and profile['adult_pilot']),
                        policy_version=POLICY_VERSION,mail_mode='local_outbox' if hasattr(self.mailer,'directory') else 'unavailable')

    def accept(self,user_id):
        with self.store.connect(write=True) as db:
            db.execute('INSERT INTO user_profiles(user_id,email_verified,policy_version,accepted_at,adult_pilot) VALUES(?,0,?,?,1) ON CONFLICT(user_id) DO UPDATE SET policy_version=excluded.policy_version,accepted_at=excluded.accepted_at,adult_pilot=1',
                       (user_id,POLICY_VERSION,int(self.clock())))

    def require_student(self,user_id):
        profile=self.profile(user_id)
        if not profile['policy_accepted']:raise HTTPException(403,'Leia e aceite os termos do piloto na área Minha conta antes de estudar.')
        if not profile['email_verified']:raise HTTPException(403,'Confirme seu e-mail na área Minha conta antes de estudar.')

    def issue(self,user_id,purpose):
        raw=secrets.token_urlsafe(32);now=int(self.clock());ttl=86400 if purpose=='verify' else 1800
        with self.store.connect(write=True) as db:
            row=db.execute('SELECT email FROM users WHERE id=?',(user_id,)).fetchone()
            if not row:raise HTTPException(401,'Entre novamente para continuar.')
            db.execute('DELETE FROM account_tokens WHERE user_id=? AND purpose=?',(user_id,purpose))
            db.execute('DELETE FROM account_tokens WHERE expires_at<=?',(now,))
            db.execute('INSERT INTO account_tokens VALUES(?,?,?,?,?)',(digest(raw),user_id,purpose,now+ttl,now))
        path='/verificar-email' if purpose=='verify' else '/recuperar-senha'
        # Fragmento não vai no request HTTP nem no Referer; a tela remove-o ao abrir.
        self.mailer.send(user_id,row['email'],purpose,self.origin+path+'#token='+raw)

    def consume(self,raw,purpose,password=None):
        encoded=hasher.hash(password) if password is not None else None
        with self.store.connect(write=True) as db:
            row=db.execute('SELECT * FROM account_tokens WHERE token_hash=? AND purpose=? AND expires_at>?',(digest(raw),purpose,int(self.clock()))).fetchone()
            if not row:raise HTTPException(400,'Link inválido, expirado ou já utilizado. Peça um novo.')
            uid=row['user_id']
            if purpose=='verify':
                db.execute('UPDATE user_profiles SET email_verified=1 WHERE user_id=?',(uid,))
            else:
                db.execute('UPDATE users SET password_hash=? WHERE id=?',(encoded,uid))
                db.execute('DELETE FROM auth_sessions WHERE user_id=?',(uid,))
            db.execute('DELETE FROM account_tokens WHERE user_id=? AND purpose=?',(uid,purpose))
        return {'ok':True}

    def request_reset(self,email):
        with self.store.connect() as db:row=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
        if row:
            try:self.issue(row['id'],'reset')
            except (HTTPException,OSError):pass # Resposta genérica também quando entrega local falha.
        return {'message':GENERIC_RESET}

    def reauthenticate(self,db,uid,password):
        row=db.execute('SELECT password_hash FROM users WHERE id=?',(uid,)).fetchone()
        if not row or not verify(row['password_hash'],password):raise HTTPException(403,'Senha incorreta. A operação não foi concluída.')

    def export(self,uid,password):
        with self.store.connect(write=True) as db:
            self.reauthenticate(db,uid,password)
            account=dict(db.execute('SELECT id,email,created_at FROM users WHERE id=?',(uid,)).fetchone())
            profile=db.execute('SELECT * FROM user_profiles WHERE user_id=?',(uid,)).fetchone()
            sessions=[dict(r) for r in db.execute('SELECT * FROM practice_sessions WHERE user_id=?',(uid,))]
            attempts=[dict(r) for r in db.execute('SELECT * FROM attempts WHERE user_id=?',(uid,))]
            exams=[dict(r) for r in db.execute('SELECT id,day,started_at,deadline,status,essay,charged_questions,quota_period FROM mock_exams WHERE user_id=?',(uid,))]
            for exam in exams:exam['responses']=[dict(r) for r in db.execute('SELECT question_id,position,choice,flagged FROM mock_items WHERE exam_id=?',(exam['id'],))]
        return dict(exported_at=int(self.clock()),account=account,profile=dict(profile) if profile else None,practice_sessions=sessions,attempts=attempts,exams=exams)

    def erase(self,uid,password):
        with self.store.connect(write=True) as db:
            self.reauthenticate(db,uid,password)
            db.execute('DELETE FROM mock_items WHERE exam_id IN (SELECT id FROM mock_exams WHERE user_id=?)',(uid,))
            db.execute('DELETE FROM mock_exams WHERE user_id=?',(uid,))
            db.execute('DELETE FROM idempotency WHERE user_id=?',(uid,))
            db.execute('DELETE FROM attempts WHERE user_id=?',(uid,))
            db.execute('DELETE FROM session_questions WHERE session_id IN (SELECT id FROM practice_sessions WHERE user_id=?)',(uid,))
            db.execute('DELETE FROM practice_sessions WHERE user_id=?',(uid,))
            db.execute('DELETE FROM auth_sessions WHERE user_id=?',(uid,))
            db.execute('DELETE FROM account_tokens WHERE user_id=?',(uid,))
            db.execute('DELETE FROM user_profiles WHERE user_id=?',(uid,))
            email=db.execute('SELECT email FROM users WHERE id=?',(uid,)).fetchone()['email']
            db.execute('DELETE FROM rate_limits WHERE bucket IN (?,?)',('account:'+digest(email),'account:'+digest('account:'+uid)))
            db.execute('DELETE FROM users WHERE id=?',(uid,))
        self.mailer.erase(uid)
        return {'ok':True,'message':'Conta e dados do piloto removidos da base ativa. Cópias exportadas por você não são apagadas.'}
