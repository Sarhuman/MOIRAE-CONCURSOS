from starlette.responses import JSONResponse


class BodyLimit:
    """Conta bytes antes do parser JSON, inclusive com Content-Length adulterado."""
    def __init__(self,app,limit=16384):
        self.app,self.limit=app,limit

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in ('POST','PUT','PATCH','DELETE'):
            return await self.app(scope,receive,send)
        chunks=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            size+=len(message.get('body',b''))
            if size>self.limit:
                return await JSONResponse({'detail':'Envio grande demais.'},status_code=413)(scope,receive,send)
            chunks.append(message.get('body',b''))
            if not message.get('more_body',False):break
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        await self.app(scope,replay,send)
