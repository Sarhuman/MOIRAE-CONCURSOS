"""Adaptador Checkout Pro restrito a sandbox; nenhuma credencial no frontend."""
import hashlib
import hmac
import re
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException


def verify_signature(payment_id,request_id,signature,secret,now):
    if not re.fullmatch(r'\d{1,30}',payment_id or '') or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',request_id or ''):
        raise HTTPException(401,'Notificação inválida.')
    try:
        parts=dict(piece.strip().split('=',1) for piece in signature.split(','))
        raw=parts['ts'];value=parts['v1'];timestamp=int(raw)
        seconds=timestamp/1000 if timestamp>10**11 else timestamp
        if abs(now-seconds)>300 or not re.fullmatch('[a-fA-F0-9]{64}',value):raise ValueError()
        manifest=f'id:{payment_id};request-id:{request_id};ts:{raw};'
        expected=hmac.new(secret.encode(),manifest.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(value.lower(),expected):raise ValueError()
    except (ValueError,KeyError,AttributeError):raise HTTPException(401,'Assinatura inválida ou expirada.')


def safe_checkout(url):
    p=urlparse(url or '')
    if p.scheme!='https' or p.hostname not in {'sandbox.mercadopago.com.br','sandbox.mercadopago.com','www.mercadopago.com.br','www.mercadopago.com'} or p.username or p.password:
        raise HTTPException(502,'Endereço de checkout inesperado.')
    return url


class MercadoPagoSandbox:
    def __init__(self,token):self.token=token

    def call(self,method,path,payload=None):
        try:
            with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
                response=client.request(method,'https://api.mercadopago.com'+path,json=payload,headers={'Authorization':'Bearer '+self.token})
                response.raise_for_status();return response.json()
        except (httpx.HTTPError,ValueError):raise HTTPException(503,'Mercado Pago indisponível. Tente novamente mais tarde.')

    def preference(self,order,plan,origin):
        payload={'items':[{'id':plan['id'],'title':'MOIRAE '+plan['name']+' · 30 dias','quantity':1,'currency_id':'BRL','unit_price':plan['price_cents']/100}],
                 'payment_methods':{'installments':1},
                 'external_reference':order['id'],'notification_url':origin+'/api/billing/webhook?source_news=webhooks',
                 'back_urls':{key:origin+'/planos' for key in ('success','failure','pending')}}
        result=self.call('POST','/checkout/preferences',payload)
        try:return dict(preference_id=str(result['id']),checkout_url=safe_checkout(result.get('sandbox_init_point')))
        except (KeyError,TypeError,AttributeError):raise HTTPException(502,'Resposta de checkout incompleta.')

    def payment(self,payment_id):return self.call('GET','/v1/payments/'+payment_id)

