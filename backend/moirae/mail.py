"""Entrega local para piloto. Nenhum e-mail é enviado pela rede."""
import json
import os
import secrets
import time
from pathlib import Path
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
