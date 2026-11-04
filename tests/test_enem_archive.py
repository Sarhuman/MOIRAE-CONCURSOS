from backend.moirae.importing.archive import selected

def test_archive_selects_color_without_duplicate_booklets():
    assert selected('https://download.inep.gov.br/enem/provas_e_gabaritos/2025_PV_impresso_D1_CD1.pdf')
    assert selected('https://download.inep.gov.br/enem/provas_e_gabaritos/2025_GB_impresso_D2_CD7.pdf')
    assert not selected('https://download.inep.gov.br/enem/provas_e_gabaritos/2025_PV_impresso_D1_CD2.pdf')
    assert not selected('https://download.inep.gov.br/enem/provas_e_gabaritos/reaplicacao_azul.pdf')
    assert selected('https://download.inep.gov.br/educacao_basica/enem/provas/1998/1998_amarela.pdf')
