"""Retrieve one regular booklet color per year from INEP's linked archive."""
import concurrent.futures
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse

BASE='https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/'

def selected(url):
    name=url.rsplit('/',1)[-1].lower()
    return ('azul' in name or bool(re.search(r'_d1_cd1\.pdf$|_d2_cd7\.pdf$',name)) or bool(re.fullmatch(r'gabarito_dia[12]\.pdf',name)) or bool(re.fullmatch(r'\d{4}_amarela\.pdf',name))) and 'reaplic' not in name and 'ppl' not in name

def retrieve(year,root):
    row=dict(year=year,source=BASE+str(year),files=[],errors=[])
    try:
        html=urlopen(row['source'],timeout=20).read().decode('utf-8')
        links=list(dict.fromkeys(re.findall(r'https://download\.inep\.gov\.br/[^"<>\s]+\.pdf',html)))
        for url in filter(selected,links):
            parsed=urlparse(url)
            if parsed.netloc!='download.inep.gov.br' or parsed.query or '..' in parsed.path:continue
            path=root/str(year)/url.rsplit('/',1)[-1];path.parent.mkdir(parents=True,exist_ok=True)
            spec=dict(url=url,name=path.name)
            try:
                if path.exists():data=path.read_bytes()
                else:
                    # Windows native trust store; curl still verifies HTTPS certificates.
                    reply=subprocess.run(['curl.exe','--fail','--silent','--show-error','--max-time','40','--max-filesize',str(40*1024*1024),url],capture_output=True,check=True)
                    data=reply.stdout
                if not data.startswith(b'%PDF-') or len(data)>40*1024*1024:raise ValueError('invalid_pdf')
                if not path.exists():path.write_bytes(data)
                spec.update(status='downloaded',sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
            except Exception as exc:spec.update(status='failed',error=type(exc).__name__)
            row['files'].append(spec)
        if not row['files']:row['errors'].append('No supported booklet found')
    except Exception as exc:row['errors'].append(type(exc).__name__)
    return row

def main():
    root=Path('var/inep/archive');root.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(lambda year:retrieve(year,root),range(2025,1997,-1)))
    target=Path('data/inep/archive-index.json');target.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(years=len(rows),downloaded=sum(f['status']=='downloaded' for r in rows for f in r['files']),failed=sum(f['status']=='failed' for r in rows for f in r['files']),page_errors=[r['year'] for r in rows if r['errors']]),ensure_ascii=False))
if __name__=='__main__':main()
