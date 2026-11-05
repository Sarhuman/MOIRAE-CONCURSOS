"""Editorial feedback for the introductory catalog; delivered after an answer only."""
DISTRACTORS = {
'mat-01': ('R$ 150 corresponderia a desconto de 25%, não 15%.', '', 'R$ 185 subtrai 15 reais, mas o desconto é percentual.', 'R$ 200 é o preço antes do desconto.', 'R$ 230 aplica aumento de 15%, em vez de desconto.'),
'mat-02': ('200 g reduz a quantidade apesar de aumentar o número de pessoas.', '350 g não mantém os 75 g por pessoa.', '400 g corresponde a menos de 75 g por pessoa para seis pessoas.', '', '600 g serviria oito pessoas na mesma proporção.'),
'mat-03': ('12 é o valor do primeiro dia, não a média.', 'A soma dividida por três é 15, não 13.', '45 dividido por três é 15, não 14.', '', '18 é o maior valor observado, não a média.'),
'lin-01': ('Uma causa poderia ser introduzida por porque; mas contrapõe ideias.', 'Uma conclusão poderia ser introduzida por portanto.', '', 'Finalidade indica objetivo, como em para estudar.', 'Adição acrescenta informação, como a conjunção e.'),
'lin-02': ('O cartaz não apresenta uma sequência narrativa.', 'Não há descrição de uma pessoa.', 'Fechar a torneira combate o desperdício.', '', 'O texto não apresenta cálculo ou relação matemática.'),
'lin-03': ('Ana é quem lê; o pronome representa o objeto lido.', '', 'O ônibus indica o lugar da leitura.', 'Comprou é um verbo, não o referente do pronome.', 'Leu é a ação cujo objeto é retomado pelo pronome.'),
'nat-01': ('Misturar resíduos dificulta sua separação e não reduz o descarte.', 'Mais embalagens tendem a aumentar os resíduos.', '', 'Queimar resíduos gera poluição e não constitui reutilização.', 'Descartar em rios causa poluição, em vez de destinação adequada.'),
'nat-02': ('2 resulta de dividir potência por tempo; energia exige multiplicação.', '5 é o tempo em horas, não a energia em Wh.', 'Somar 10 e 5 não calcula energia.', '', '10 vezes 5 é 50, não 500.'),
'nat-03': ('Condensação é a passagem de gás para líquido.', 'Solidificação é a passagem de líquido para sólido.', '', 'Fusão é a passagem de sólido para líquido.', 'Precipitação é a queda de água da atmosfera, como chuva.'),
'hum-01': ('20 m equivale a 2.000 cm, não 200.000 cm.', '200 m equivale a 20.000 cm; falta um fator dez.', '', '20 km excede em dez vezes a distância representada.', '200 km excede em cem vezes a distância representada.'),
'hum-02': ('', 'Impedir informações limita a participação informada.', 'Proibir debates impede a discussão coletiva.', 'Ignorar consultas não representa participação em decisões.', 'Excluir moradores reduz a participação da comunidade.'),
'hum-03': ('Mudança definitiva é migração, sem o retorno recorrente descrito.', 'Uma viagem isolada não tem a recorrência do deslocamento pendular.', '', 'Troca permanente de residência não é trajeto recorrente de ida e volta.', 'A ausência de retorno não caracteriza deslocamento pendular.'),
}

def alternative_feedback(question):
    return [dict(id=chr(97+i),text=text,correct=chr(97+i)==question.answer,
                 explanation=question.explanation if chr(97+i)==question.answer else (question.alternative_explanations or DISTRACTORS[question.id])[i])
            for i,text in enumerate(question.options)]
