"""ETL conservador: originais imutáveis, rascunhos e revisão obrigatória."""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_PDF=40*1024*1024
QUESTION=re.compile(r'QUEST[ÃA]O\s+(\d{1,3})\b',re.IGNORECASE)
KEY=re.compile(r'\b(\d{1,3})\s*[-–.:]?\s+(ANULAD[AO]|EXCLU[IÍ]D[AO]|[ABCDE])\b',re.IGNORECASE)


class ImportFailure(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ImportFailure('Redirecionamento inesperado: confira a fonte oficial antes de continuar.')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def validate_url(url):
    p=urlparse(url)
    if (p.scheme!='https' or p.netloc!='download.inep.gov.br' or p.query or p.fragment
            or not re.fullmatch(r'/enem/provas_e_gabaritos/[A-Za-z0-9_]+\.pdf',p.path)):
        raise ImportFailure('Somente PDFs HTTPS do diretório oficial do Inep são aceitos.')
    return p.path.rsplit('/',1)[1]


def validate_manifest(manifest):
    if not isinstance(manifest.get('edition'),int) or not 1998<=manifest['edition']<=2100:
        raise ImportFailure('Edição inválida.')
    expected_page=f"https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/{manifest['edition']}"
    if manifest.get('source_page')!=expected_page:raise ImportFailure('Página de origem não corresponde à edição oficial.')
    if manifest.get('application')!='regular':
        raise ImportFailure('Este primeiro importador aceita apenas aplicação regular.')
    if len(manifest.get('booklets',[]))!=2 or {s['day'] for s in manifest['booklets']}!={1,2}:
        raise ImportFailure('Informe exatamente um caderno por dia.')
    for spec in manifest['booklets']:
        for kind,tag in [('exam','PV'),('key','GB')]:
            name=validate_url(spec[kind+'_url'])
            expected=f"{manifest['edition']}_{tag}_impresso_D{spec['day']}_CD{spec['booklet']}.pdf"
            if name!=expected:raise ImportFailure('URL e identificação do caderno não correspondem.')


def validate_pdf(data):
    if not data.startswith(b'%PDF-') or len(data)>MAX_PDF:
        raise ImportFailure('Arquivo não é um PDF válido ou excede o limite de tamanho.')


def download(url,directory):
    name=validate_url(url)
    request=Request(url,headers={'User-Agent':'MOIRAE-content-import/1.0'})
    with build_opener(NoRedirect).open(request,timeout=30) as response:
        data=response.read(MAX_PDF+1)
    validate_pdf(data)
    path=Path(directory)/name
    path.parent.mkdir(parents=True,exist_ok=True)
    # O arquivo recebido tem caminho controlado e é validado antes da gravação.
    if path.exists() and path.read_bytes()!=data:
        raise ImportFailure('A fonte mudou. Use outro diretório para preservar a versão anterior.')
    path.write_bytes(data)
    return path


def read_pdf(path):
    data=Path(path).read_bytes();validate_pdf(data)
    pdf=PdfReader(path)
    if pdf.is_encrypted:raise ImportFailure('PDF criptografado não suportado.')
    if not 1<=len(pdf.pages)<=150:raise ImportFailure('Número de páginas inesperado.')
    return data,[page.extract_text(extraction_mode='layout') or '' for page in pdf.pages]


def split_questions(pages,day):
    """Preserva todo o bloco extraído, sem fingir separar opções ou imagens."""
    joined='';boundaries=[]
    for index,text in enumerate(pages,1):
        boundaries.append((len(joined),index));joined+=text+'\n'
    matches=list(QUESTION.finditer(joined));counts=defaultdict(int);records=[]
    for index,match in enumerate(matches):
        number=int(match.group(1))
        if not (1<=number<=90 if day==1 else 91<=number<=180):continue
        counts[number]+=1
        start,end=match.start(),matches[index+1].start() if index+1<len(matches) else len(joined)
        raw=joined[start:end].strip()
        first_page=max(page for offset,page in boundaries if offset<=start)
        last_page=max(page for offset,page in boundaries if offset<end)
        flags=['text_order_unreviewed','alternatives_unreviewed','figures_and_shared_text_unreviewed','rights_unreviewed','explanation_missing']
        language='none'
        if day==1 and number<=5:
            # Não presumir ordem inglês/espanhol: é uma decisão editorial com conferência no PDF.
            language=f'unresolved-{counts[number]}'
            flags.append('foreign_language_unresolved')
        elif counts[number]>1:
            flags.append('duplicate_question_heading')
        records.append(dict(number=number,occurrence=counts[number],language=language,
                            pages=list(range(first_page,last_page+1)),raw_text=raw,flags=flags))
    return records


def parse_key(pages):
    entries=defaultdict(list)
    for page in pages:
        for match in KEY.finditer(page):
            number=int(match.group(1));token=match.group(2).upper()
            entries[number].append(dict(answer=token.lower() if token in 'ABCDE' else None,
                                         status='valid' if token in 'ABCDE' else 'annulled'))
    return dict(entries)


def run(manifest,input_dir,output_dir):
    validate_manifest(manifest)
    out=Path(output_dir)
    if out.exists():raise ImportFailure('A saída já existe; use outro diretório para não sobrescrever revisão anterior.')
    records=[];sources=[];reports=[]
    # Ler todos os arquivos antes de produzir saída: falha de download não vira importação parcial.
    extracted=[]
    for spec in manifest['booklets']:
        parts={}
        for kind in ('exam','key'):
            path=Path(input_dir)/validate_url(spec[kind+'_url'])
            if not path.is_file():raise ImportFailure(f'Arquivo necessário ausente: {path.name}')
            data,pages=read_pdf(path)
            parts[kind]=(data,pages)
        extracted.append((spec,parts))
    for spec,parts in extracted:
        exam_data,exam_pages=parts['exam'];key_data,key_pages=parts['key']
        exam_hash,key_hash=sha256(exam_data),sha256(key_data)
        keys=parse_key(key_pages)
        candidates=split_questions(exam_pages,spec['day'])
        expected=set(range(1,91) if spec['day']==1 else range(91,181))
        seen={r['number'] for r in candidates}
        for kind,data in [('exam',exam_data),('key',key_data)]:
            sources.append(dict(kind=kind,day=spec['day'],booklet=spec['booklet'],url=spec[kind+'_url'],sha256=sha256(data),size_bytes=len(data)))
        for row in candidates:
            answers=keys.get(row['number'],[])
            # Só vincular quando há correspondência inequívoca; línguas estrangeiras ficam pendentes.
            answer=answers[0] if len(answers)==1 and row['language']=='none' else None
            if answer is None:row['flags'].append('answer_missing_or_ambiguous')
            elif answer['status']=='annulled':row['flags'].append('officially_annulled')
            row.update(id=f"enem-{manifest['edition']}-{manifest['application']}-d{spec['day']}-cd{spec['booklet']}-q{row['number']:03d}-{row['language']}-o{row['occurrence']}",
                       edition=manifest['edition'],application=manifest['application'],day=spec['day'],booklet=spec['booklet'],color=spec['color'],
                       exam_sha256=exam_hash,key_sha256=key_hash,source_page=manifest['source_page'],exam_url=spec['exam_url'],key_url=spec['key_url'],
                       answer=answer['answer'] if answer else None,key_status=answer['status'] if answer else 'unresolved',
                       key_candidates=answers,status='draft',editorial_review=False,rights_review=False)
            records.append(row)
        reports.append(dict(day=spec['day'],candidate_count=len(candidates),expected_candidate_count=95 if spec['day']==1 else 90,expected_distinct_numbers=90,
                            foreign_language_occurrences={str(n):sum(r['number']==n for r in candidates) for n in range(1,6)} if spec['day']==1 else {},
                            missing_question_numbers=sorted(expected-seen),missing_key_numbers=sorted(expected-set(keys)),
                            ambiguous_key_numbers=sorted(n for n in expected if len(keys.get(n,[]))>1)))
    fingerprint=sha256(json.dumps(sources,sort_keys=True).encode())
    report=dict(edition=manifest['edition'],application=manifest['application'],status='needs_review',
                batch_sha256=fingerprint,imported_at=datetime.now(timezone.utc).isoformat(),sources=sources,
                candidate_count=len(records),published_count=0,booklets=reports)
    out.mkdir(parents=True)
    (out/'candidates.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--input-dir',required=True)
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--download',action='store_true',help='Baixar os quatro PDFs oficiais antes de extrair.')
    args=parser.parse_args(argv)
    try:
        manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'));validate_manifest(manifest)
        if Path(args.output_dir).exists():raise ImportFailure('Saída existente: use um novo diretório.')
        if args.download:
            for spec in manifest['booklets']:
                for kind in ('exam','key'):download(spec[kind+'_url'],args.input_dir)
        report=run(manifest,args.input_dir,args.output_dir)
        print(json.dumps(dict(status=report['status'],candidates=report['candidate_count'],published=0,batch_sha256=report['batch_sha256'])))
        return 0
    except (ImportFailure,OSError,ValueError,KeyError,PyPdfError) as error:
        print('Importação não concluída: '+str(error),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
