"""Initial sample based on a completed, explicitly selected diagnostic session."""
from .catalog import BY_ID

def result(store,uid):
    with store.connect() as db:
        session=db.execute('SELECT s.* FROM practice_sessions s JOIN diagnostic_sessions d ON d.session_id=s.id WHERE s.user_id=? ORDER BY s.created_at DESC,s.rowid DESC LIMIT 1',(uid,)).fetchone()
        if not session:return dict(status='not_started',areas=[])
        rows=db.execute('SELECT question_id,correct FROM attempts WHERE session_id=?',(session['id'],)).fetchall()
    areas={}
    for row in rows:
        area=BY_ID[row['question_id']].area
        value=areas.setdefault(area,dict(area=area,answered=0,errors=0))
        value['answered']+=1;value['errors']+=1-row['correct']
    ranked=sorted(areas.values(),key=lambda x:(-x['errors'],x['area']))
    completed=session['status']=='completed'
    focus=ranked[0]['area'] if completed and ranked and ranked[0]['errors'] else None
    return dict(status=session['status'],answered=len(rows),areas=ranked if completed else [],focus=focus,
                recommendation=(f'Comece revisando os erros de {focus}. Depois faça uma sessão de 15 minutos.' if focus else 'Comece com uma sessão de 15 minutos para explorar novos conteúdos.') if completed else 'Continue as cinco questões antes de consultar o resultado.',
                notice=f'Amostra observada: {len(rows)} questões respondidas em {len(areas)} áreas. Diagnósticos novos têm cinco questões introdutórias das quatro áreas. Não mede domínio, não avalia redação e não prevê nota do ENEM. As revisões respeitam o agendamento; planejamento e caderno exigem plano ativo.')
