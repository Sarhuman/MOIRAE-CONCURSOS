"""Offline comparison of externally supplied human scores and recorded predictions."""
import argparse
import json
from pathlib import Path

def scores(value):
    if not isinstance(value,dict) or set(value)!=set('12345'):raise ValueError('Informe C1–C5 nas chaves 1 a 5.')
    if any(type(v) is not int or v not in (0,40,80,120,160,200) for v in value.values()):raise ValueError('Notas devem ser inteiros de 0 a 200, em passos de 40.')
    return value

def compare(rows):
    if not isinstance(rows,list) or not rows:raise ValueError('Corpus vazio não produz avaliação.')
    seen=set();groups={}
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'] or row['id'] in seen:raise ValueError('IDs ausentes ou repetidos.')
        seen.add(row['id'])
        if row.get('human_reviewed') is not True or row.get('authorized_use') is not True:raise ValueError('Exige referência humana e uso autorizado declarados em cada caso.')
        key=tuple(row.get(k) for k in ('model','rubric_version','prompt_version'))
        if not all(isinstance(v,str) and v for v in key):raise ValueError('Modelo e versões devem ser informados.')
        human,predicted=scores(row.get('human_scores')),scores(row.get('predicted_scores'))
        group=groups.setdefault(key,[]);group.append({c:abs(human[c]-predicted[c]) for c in '12345'})
    return dict(cases=len(rows),groups=[dict(model=k[0],rubric_version=k[1],prompt_version=k[2],cases=len(v),
        competencies={c:dict(mean_absolute_error=round(sum(r[c] for r in v)/len(v),2),exact_agreement=round(sum(r[c]==0 for r in v)/len(v),4),within_40=round(sum(r[c]<=40 for r in v)/len(v),4)) for c in '12345'}) for k,v in groups.items()],
        approved=False,notice='Métricas descritivas de notas. Não avaliam qualidade dos comentários, vieses ou direitos de uso. Não habilitam a integração nem aprovam o modelo.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('corpus');args=parser.parse_args()
    try:report=compare(json.loads(Path(args.corpus).read_text()))
    except (ValueError,OSError,TypeError):parser.error('Corpus inválido. Confira o formato documentado; conteúdo não será exibido.')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
