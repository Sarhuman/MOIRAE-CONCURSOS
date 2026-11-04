"""PDFs sintéticos autorais: os testes não baixam nem reproduzem provas do Inep."""
import copy
import json
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from backend.moirae.importing.inep import (ImportFailure,validate_manifest,validate_url,split_questions,parse_key,run,download,main)


def pdf(path,lines):
    writer=PdfWriter();page=writer.add_blank_page(width=595,height=842)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();commands=['BT /F1 11 Tf 40 790 Td']
    for text in lines:
        escaped=text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        commands.append(f'({escaped}) Tj 0 -18 Td')
    commands.append('ET');stream.set_data('\n'.join(commands).encode('ascii'))
    page[NameObject('/Contents')]=writer._add_object(stream)
    with path.open('wb') as f:writer.write(f)


@pytest.fixture
def fixture(tmp_path):
    manifest=json.loads(open('data/inep/enem-2025-regular-blue.json').read())
    source=tmp_path/'originals';source.mkdir()
    for spec in manifest['booklets']:
        n=6 if spec['day']==1 else 91
        pdf(source/validate_url(spec['exam_url']),[f'QUESTAO {n:03d}','Exemplo sintetico autoral para teste.','A primeira alternativa','B segunda alternativa',f'QUESTAO {n+1:03d}','Outro exemplo sintetico.'])
        pdf(source/validate_url(spec['key_url']),[f'{n:03d} A',f'{n+1:03d} ANULADA'])
    return manifest,source,tmp_path/'output'


def test_pdf_to_draft_end_to_end(fixture):
    manifest,source,out=fixture
    report=run(manifest,source,out)
    assert report['candidate_count']==4 and report['published_count']==0
    assert len(report['sources'])==4
    assert all(len(s['sha256'])==64 for s in report['sources'])
    rows=json.loads((out/'candidates.json').read_text(encoding='utf-8'))
    assert all(r['status']=='draft' and not r['editorial_review'] and not r['rights_review'] for r in rows)
    assert rows[0]['answer']=='a'
    assert rows[1]['key_status']=='annulled' and rows[1]['answer'] is None
    assert 8 in report['booklets'][0]['missing_question_numbers']
    assert rows[0]['pages']==[1]


def test_batch_hash_stable_and_no_overwrite(fixture,tmp_path):
    manifest,source,out=fixture
    first=run(manifest,source,out)
    second=run(manifest,source,tmp_path/'another')
    assert first['batch_sha256']==second['batch_sha256']
    with pytest.raises(ImportFailure):run(manifest,source,out)


def test_missing_original_does_not_create_partial_output(fixture):
    manifest,source,out=fixture
    (source/validate_url(manifest['booklets'][1]['key_url'])).unlink()
    with pytest.raises(ImportFailure):run(manifest,source,out)
    assert not out.exists()


def test_foreign_language_duplicates_are_not_silently_merged():
    rows=split_questions(['QUESTAO 001\nEnglish synthetic\nQUESTAO 001\nSpanish synthetic\nQUESTAO 006\nCommon'],1)
    assert len(rows)==3 and rows[0]['language']!=rows[1]['language']
    assert all('foreign_language_unresolved' in r['flags'] for r in rows[:2])


def test_key_parser_ambiguity_and_annulment():
    keys=parse_key(['001 A   006 B\n001 C\n007 ANULADA\n008 EXCLUIDA'])
    assert len(keys[1])==2 and keys[6][0]['answer']=='b'
    assert keys[7][0]['status']=='annulled' and keys[8][0]['answer'] is None


@pytest.mark.parametrize('url', ['http://download.inep.gov.br/enem/provas_e_gabaritos/x.pdf','https://evil.test/x.pdf','https://download.inep.gov.br@evil.test/x.pdf','https://download.inep.gov.br/enem/provas_e_gabaritos/../../x.pdf','https://download.inep.gov.br/enem/provas_e_gabaritos/x.pdf?next=evil'])
def test_untrusted_urls_rejected(url):
    with pytest.raises(ImportFailure):validate_url(url)


def test_manifest_mismatched_booklet_rejected(fixture):
    manifest,_,_=fixture;bad=copy.deepcopy(manifest);bad['booklets'][0]['booklet']=2
    with pytest.raises(ImportFailure):validate_manifest(bad)


def test_fake_pdf_rejected_without_output(fixture):
    manifest,source,out=fixture;(source/validate_url(manifest['booklets'][0]['exam_url'])).write_text('<html>503</html>')
    with pytest.raises(ImportFailure):run(manifest,source,out)
    assert not out.exists()


def test_failed_download_does_not_write_invalid_pdf(tmp_path,monkeypatch):
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'<html>Service unavailable</html>'
    class Opener:
        def open(self,*args,**kwargs):return Reply()
    monkeypatch.setattr('backend.moirae.importing.inep.build_opener',lambda *a:Opener())
    with pytest.raises(ImportFailure):download('https://download.inep.gov.br/enem/provas_e_gabaritos/test.pdf',tmp_path)
    assert not list(tmp_path.iterdir())


def test_cli_missing_files_returns_failure(fixture,tmp_path,capsys):
    manifest,source,out=fixture;p=tmp_path/'manifest.json';p.write_text(json.dumps(manifest))
    status=main(['--manifest',str(p),'--input-dir',str(tmp_path/'missing'),'--output-dir',str(out)])
    assert status==1 and not out.exists()
    assert 'não concluída' in capsys.readouterr().err

def test_spaced_question_heading_from_pdf_font_layout():
    rows=split_questions(['Q\nU\nESTÃ O 01\nTexto de teste\nQU EST Ã O 02\nOutro texto'],1)
    assert [row['number'] for row in rows]==[1,2]
