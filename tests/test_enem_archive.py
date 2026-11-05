from backend.moirae.importing.archive import selected

def test_archive_selects_color_without_duplicate_booklets():
    assert selected('https://download.inep.gov.br/enem/provas_e_gabaritos/2025_PV_impresso_D1_CD1.pdf')
    assert selected('https://download.inep.gov.br/enem/provas_e_gabaritos/2025_GB_impresso_D2_CD7.pdf')
    assert not selected('https://download.inep.gov.br/enem/provas_e_gabaritos/2025_PV_impresso_D1_CD2.pdf')
    assert not selected('https://download.inep.gov.br/enem/provas_e_gabaritos/reaplicacao_azul.pdf')
    assert selected('https://download.inep.gov.br/educacao_basica/enem/provas/1998/1998_amarela.pdf')


def test_archive_reports_instance_availability_and_preserves_official_fallback(tmp_path,monkeypatch):
    import json
    from fastapi.testclient import TestClient
    from test_mvp import register
    import backend.moirae.app as module
    app=module.create_app(str(tmp_path/'test.sqlite3'),origin='http://localhost:8000',secure=False)
    root=tmp_path/'instance';(root/'data'/'inep').mkdir(parents=True)
    name='2025_PV_impresso_D2_CD7.pdf'
    url='https://download.inep.gov.br/enem/provas_e_gabaritos/'+name
    (root/'data'/'inep'/'archive-index.json').write_text(json.dumps([dict(year=2025,files=[dict(name=name,status='downloaded',url=url)])]))
    monkeypatch.setattr(module,'ROOT',root)
    c=TestClient(app,base_url='http://localhost:8000',headers={'Origin':'http://localhost:8000'})
    register(c)
    index=c.get('/api/enem-archive')
    assert index.headers['cache-control']=='no-store'
    entry=index.json()[0]['files'][0]
    assert entry['available_local'] is False and entry['url']==url
    assert c.get('/acervo-enem/2025/'+name).status_code==404
    folder=root/'var'/'inep'/'archive'/'2025';folder.mkdir(parents=True)
    (folder/name).write_bytes(b'%PDF-test')
    assert c.get('/api/enem-archive').json()[0]['files'][0]['available_local'] is True
    pdf=c.get('/acervo-enem/2025/'+name)
    assert pdf.content==b'%PDF-test' and pdf.headers['cache-control']=='private, no-store'
    assert c.get('/acervo-enem/2025/unknown.pdf').status_code==404
