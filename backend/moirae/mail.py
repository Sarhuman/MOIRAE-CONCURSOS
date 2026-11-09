"""Adaptadores de entrega de e-mail do piloto."""
import json
import os
import secrets
import time
from pathlib import Path
import httpx
from fastapi import HTTPException


class LocalMail:
    def __init__(self,directory):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(self.directory,0o700)
        self.messages=[]

    def send(self,user_id,email,purpose,link):
        message=dict(user_id=user_id,to=email,purpose=purpose,link=link,created_at=int(time.time()))
        path=self.directory/f'{user_id}-{secrets.token_hex(8)}.json'
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:json.dump(message,stream,ensure_ascii=False)
        self.messages.append(message)

    def erase(self,user_id):
        for path in self.directory.glob(f'{user_id}-*.json'):path.unlink(missing_ok=True)
        self.messages[:]=[m for m in self.messages if m['user_id']!=user_id]


class MailUnavailable:
    def send(self,*args):
        raise HTTPException(503,'A entrega de e-mails ainda não foi configurada. O cadastro público está indisponível.')
    def erase(self,*args):pass


class ResendMail:
    mode = 'resend'

    def __init__(self, api_key, sender, transport=None):
        self.api_key = api_key
        self.sender = sender
        self.transport = transport

    def send(self, user_id, email, purpose, link):
        subject, instruction = {
            'verify': ('Confirme seu e-mail no MOIRAE', 'Confirme seu cadastro em até 24 horas.'),
            'reset': ('Recupere sua senha no MOIRAE', 'Redefina sua senha em até 30 minutos.'),
        }[purpose]
        payload = {
            'from': self.sender,
            'to': [email],
            'subject': subject,
            'text': f'{instruction}\n\n{link}\n\nSe você não fez a solicitação, ignore esta mensagem.',
        }
        try:
            with httpx.Client(timeout=5.0, trust_env=False, transport=self.transport) as client:
                response = client.post(
                    'https://api.resend.com/emails',
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(503, 'Não foi possível enviar o e-mail agora. Tente novamente mais tarde.') from None

    def erase(self, user_id):
        """Este adaptador não grava mensagens no disco local."""


def configured_mail(origin, secure, database_path):
    if os.getenv('MOIRAE_EMAIL_PROVIDER', '').lower() == 'resend':
        key = os.getenv('RESEND_API_KEY', '').strip()
        sender = os.getenv('MOIRAE_EMAIL_FROM', '').strip()
        if not origin.startswith('https://') or not secure or not key or not sender:
            raise ValueError('Resend exige origem HTTPS, cookie Secure, chave e remetente.')
        return ResendMail(key, sender)
    if not secure:
        return LocalMail(Path(database_path).parent / 'mail-outbox')
    return MailUnavailable()
