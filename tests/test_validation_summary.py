import importlib.util
from pathlib import Path
import sys
import pytest

spec=importlib.util.spec_from_file_location('validation_summary',Path('scripts/validation_summary.py'))
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)


def write(tmp_path,text):
    path=tmp_path/'junit.xml';path.write_text(text,encoding='utf-8');return path


def test_nested_suites_are_not_double_counted_or_leaked(tmp_path):
    path=write(tmp_path,'<testsuites tests="9"><testsuite tests="9"><testcase name="PRIVATE-TOKEN"><system-out>PRIVATE-OUTPUT</system-out></testcase><testsuite tests="1"><testcase><failure message="PRIVATE-FAILURE"/></testcase></testsuite><testcase><error/></testcase><testcase><skipped/></testcase></testsuite></testsuites>')
    counts=module.read_counts(path)
    assert (counts.total,counts.passed,counts.failed,counts.errors,counts.skipped)==(4,1,1,1,1)
    text,complete=module.render(path,'backend-windows','failure',compile_outcome='skipped',sha='a'*40)
    assert not complete and '| 4 | 1 | 1 | 1 | 1 |' in text
    assert 'PRIVATE' not in text


@pytest.mark.parametrize('xml',['<invalid/>','<testsuite/>','<testsuite>','<!DOCTYPE foo [<!ENTITY x "secret">]><testsuite/>'])
def test_invalid_reports_never_pass(tmp_path,xml):
    path=write(tmp_path,xml)
    text,complete=module.render(path,'backend-ubuntu','success',compile_outcome='success')
    assert not complete and 'Não interpretar como aprovação' in text


def test_missing_report_is_not_a_success(tmp_path):
    text,complete=module.render(tmp_path/'missing.xml','frontend','success',syntax_outcome='success')
    assert not complete and 'ausente' in text


def test_successful_tests_cannot_hide_skipped_compilation(tmp_path):
    path=write(tmp_path,'<testsuite><testcase/></testsuite>')
    text,complete=module.render(path,'backend-ubuntu','success',compile_outcome='skipped')
    assert not complete and 'não executado' in text


def test_summary_accepts_only_known_metadata_and_never_dumps_environment(tmp_path,monkeypatch):
    path=write(tmp_path,'<testsuites><testsuite><testcase/></testsuite></testsuites>')
    summary=tmp_path/'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY',str(summary))
    monkeypatch.setenv('VALIDATION_TEST_OUTCOME','success')
    monkeypatch.setenv('VALIDATION_SYNTAX_OUTCOME','success')
    monkeypatch.setenv('OPENAI_API_KEY','PRIVATE-KEY')
    monkeypatch.setenv('GITHUB_SHA','private\n[bad](https://bad.test)')
    assert module.main(['--junit',str(path),'--label','frontend'])==0
    text=summary.read_text(encoding='utf-8')
    assert 'PRIVATE' not in text and 'https://bad.test' not in text
    assert 'não informado' in text and 'verificações concluídas' in text


def test_size_limit_rejects_oversized_reports(tmp_path,monkeypatch):
    path=write(tmp_path,'<testsuite><testcase/></testsuite>')
    monkeypatch.setattr(module,'MAX_REPORT_BYTES',4)
    with pytest.raises(ValueError):module.read_counts(path)


def test_all_skipped_does_not_approve_a_suite(tmp_path):
    path=write(tmp_path,'<testsuite><testcase><skipped/></testcase></testsuite>')
    _,complete=module.render(path,'backend-windows','success',compile_outcome='success')
    assert not complete

def test_utf16_entity_document_is_not_accepted(tmp_path):
    path=tmp_path/'junit.xml'
    path.write_bytes('<!DOCTYPE foo [<!ENTITY x "secret">]><testsuite><testcase name="&x;"/></testsuite>'.encode('utf-16'))
    _,complete=module.render(path,'backend-ubuntu','success',compile_outcome='success')
    assert not complete
