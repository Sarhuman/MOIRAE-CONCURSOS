"""Publish counts only to GitHub's job summary; never copy test logs or credentials."""
import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

MAX_REPORT_BYTES=10*1024*1024
LABELS={'backend-ubuntu':'Backend · Ubuntu','backend-windows':'Backend · Windows','frontend':'Frontend · Node.js'}
OUTCOMES={'success':'aprovado','failure':'falhou','cancelled':'cancelado','skipped':'não executado','unknown':'sem resultado'}


@dataclass(frozen=True)
class Counts:
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int


def read_counts(path):
    with Path(path).open('rb') as report:
        content=report.read(MAX_REPORT_BYTES+1)
    if len(content)>MAX_REPORT_BYTES:raise ValueError('Relatório excede o limite.')
    content=content.decode('utf-8-sig')
    if re.search(r'<!\s*(DOCTYPE|ENTITY)\b',content,re.IGNORECASE):
        raise ValueError('Declaração XML não permitida.')
    root=ET.fromstring(content)
    if root.tag not in ('testsuite','testsuites'):raise ValueError('Raiz JUnit inválida.')
    cases=list(root.iter('testcase'))
    if not cases:raise ValueError('Relatório sem casos de teste.')
    failed=errors=skipped=passed=0
    for case in cases:
        # Count each testcase once. Aggregate suite counters may include child suites.
        if case.find('error') is not None:errors+=1
        elif case.find('failure') is not None:failed+=1
        elif case.find('skipped') is not None:skipped+=1
        else:passed+=1
    return Counts(len(cases),passed,failed,errors,skipped)


def render(path,label,test_outcome,syntax_outcome='unknown',compile_outcome='unknown',sha=''):
    if label not in LABELS:raise ValueError('Rótulo inválido.')
    counts=None
    try:counts=read_counts(path)
    except (OSError,ValueError,ET.ParseError):pass
    valid=counts is not None
    tests_ok=test_outcome=='success' and valid and counts.passed>0 and counts.failed==0 and counts.errors==0 and counts.skipped==0
    status='aprovado' if tests_ok else 'pendente/ausente' if test_outcome in ('skipped','cancelled','unknown') else 'não aprovado'
    commit=sha if re.fullmatch('[0-9a-fA-F]{40}',sha or '') else 'não informado'
    rows=[f'## Validação automática · {LABELS[label]}','',f'**Testes: {status}.**',f'Commit testado pelo runner: `{commit}`.','']
    if counts:
        rows+=['| Casos | Aprovados | Falhas | Erros | Ignorados |','| --- | --- | --- | --- | --- |',f'| {counts.total} | {counts.passed} | {counts.failed} | {counts.errors} | {counts.skipped} |','']
    else:
        rows+=['Relatório JUnit ausente, inválido ou sem casos. Não interpretar como aprovação.','']
    if label=='frontend':rows+=[f"Sintaxe web: **{OUTCOMES.get(syntax_outcome,'sem resultado')}**.",'']
    else:rows+=[f"Compilação Python: **{OUTCOMES.get(compile_outcome,'sem resultado')}**.",'']
    rows+=['### Limites desta evidência','',
           '- Este resumo contém apenas contagens e estados, sem mensagens dos testes, textos, tokens ou variáveis de ambiente.',
           '- Windows e Ubuntu executam a mesma suíte Python; não somar as contagens como testes distintos.',
           '- Testes com provedor falso não comprovam pagamento externo ou homologação Mercado Pago.',
           '- Navegação autenticada, celular físico, teclado, zoom e capturas reais continuam pendentes de conferência manual.',
           '- Nenhuma campanha, cobrança real, correção OpenAI ou publicação é habilitada por este workflow.','']
    # A skipped/failed compilation or syntax check must not be hidden by passing tests.
    supplemental=syntax_outcome if label=='frontend' else compile_outcome
    complete=tests_ok and supplemental=='success'
    rows+=['**Resultado do job: '+('verificações concluídas' if complete else 'há verificação ausente ou não aprovada')+'.**','']
    return '\n'.join(rows),complete


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--junit',required=True)
    parser.add_argument('--label',required=True,choices=LABELS)
    args=parser.parse_args(argv)
    summary,complete=render(args.junit,args.label,os.getenv('VALIDATION_TEST_OUTCOME','unknown'),os.getenv('VALIDATION_SYNTAX_OUTCOME','unknown'),os.getenv('VALIDATION_COMPILE_OUTCOME','unknown'),os.getenv('GITHUB_SHA',''))
    destination=os.getenv('GITHUB_STEP_SUMMARY')
    if destination:
        with Path(destination).open('a',encoding='utf-8') as stream:stream.write(summary)
    else:print(summary)
    return 0 if complete else 1


if __name__=='__main__':raise SystemExit(main())
