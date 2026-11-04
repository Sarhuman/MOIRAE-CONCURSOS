"""Questões autorais introdutórias. Não são itens oficiais nem calibrados ENEM."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str
    area: str
    subject: str
    prompt: str
    options: tuple[str, ...]
    answer: str
    explanation: str
    provenance: dict | None = None
    alternative_explanations: tuple[str, ...] = ()

    def public(self):
        return dict(id=self.id, area=self.area, subject=self.subject, prompt=self.prompt,
                    options=[dict(id=chr(97+i), text=t) for i, t in enumerate(self.options)],
                    source=(f"ENEM 2025 · 2º dia · Caderno 7 azul · Questão {self.provenance['number']}" if self.provenance else 'Questão autoral introdutória do MOIRAE; não oficial do ENEM.'),provenance=self.provenance)


QUESTIONS = [
    Question('mat-01','Matemática','Porcentagem','Uma mochila de R$ 200 recebe 15% de desconto. Qual é o preço final?',('R$ 150','R$ 170','R$ 185','R$ 200','R$ 230'),'b','15% de 200 é 30. Portanto, 200 − 30 = R$ 170.'),
    Question('mat-02','Matemática','Proporção','Uma receita para 4 pessoas usa 300 g de arroz. Mantendo a proporção, quanto usar para 6 pessoas?',('200 g','350 g','400 g','450 g','600 g'),'d','Cada pessoa corresponde a 75 g. Para 6 pessoas: 6 × 75 = 450 g.'),
    Question('mat-03','Matemática','Média','Uma estudante resolveu 12, 18 e 15 questões em três dias. Qual foi a média diária?',('12','13','14','15','18'),'d','Somamos 12 + 18 + 15 = 45 e dividimos pelos 3 dias: 15.'),
    Question('lin-01','Linguagens','Coesão','Em “Estudou bastante, mas não terminou a prova”, a palavra “mas” expressa:',('Causa','Conclusão','Oposição','Finalidade','Adição'),'c','“Mas” introduz uma oposição à expectativa criada pela primeira oração.'),
    Question('lin-02','Linguagens','Interpretação','Um cartaz diz: “Feche a torneira enquanto escova os dentes.” Qual é sua finalidade principal?',('Narrar uma história','Descrever uma pessoa','Defender o desperdício','Orientar uma ação para economizar água','Apresentar uma fórmula'),'d','O imperativo “feche” orienta uma ação concreta para reduzir o consumo de água.'),
    Question('lin-03','Linguagens','Referência textual','Em “Ana comprou um livro e o leu no ônibus”, o pronome “o” retoma:',('Ana','Livro','Ônibus','Comprou','Leu'),'b','O pronome funciona como objeto de “leu” e substitui “um livro”.'),
    Question('nat-01','Natureza','Ecologia','Qual ação reduz diretamente a quantidade de resíduos enviados a um aterro?',('Misturar todos os resíduos','Descartar mais embalagens','Reutilizar um recipiente antes de descartá-lo','Queimar resíduos no quintal','Jogar resíduos em rios'),'c','Reutilizar prolonga o uso do objeto e evita ou adia seu descarte.'),
    Question('nat-02','Natureza','Energia','Uma lâmpada de 10 W permanece ligada por 5 horas. Qual é a energia consumida?',('2 Wh','5 Wh','15 Wh','50 Wh','500 Wh'),'d','Energia = potência × tempo: 10 W × 5 h = 50 Wh.'),
    Question('nat-03','Natureza','Ciclo da água','A passagem da água líquida para o estado gasoso na superfície de um lago é chamada de:',('Condensação','Solidificação','Evaporação','Fusão','Precipitação'),'c','Evaporação é a passagem do líquido para o estado gasoso pela superfície.'),
    Question('hum-01','Humanas','Cartografia','Em um mapa na escala 1:100.000, uma distância de 2 cm representa:',('20 m','200 m','2 km','20 km','200 km'),'c','2 × 100.000 = 200.000 cm, equivalentes a 2.000 m ou 2 km.'),
    Question('hum-02','Humanas','Cidadania','Qual situação exemplifica a participação da população em decisões públicas?',('Participar de uma audiência pública sobre transporte','Impedir a divulgação de informações públicas','Proibir debates comunitários','Ignorar todas as consultas públicas','Excluir moradores de uma discussão'),'a','Uma audiência pública abre espaço para que moradores apresentem demandas e discutam propostas.'),
    Question('hum-03','Humanas','Urbanização','Qual situação caracteriza um deslocamento pendular?',('Mudar de país definitivamente','Viajar uma única vez nas férias','Ir diariamente de uma cidade à outra para trabalhar e retornar','Trocar permanentemente de residência','Migrar sem previsão de volta'),'c','O deslocamento pendular envolve trajetos recorrentes entre moradia e trabalho ou estudo, com retorno.'),
]
import json
from pathlib import Path
for item in json.loads((Path(__file__).resolve().parents[2]/'data'/'inep'/'enem-2025-validated.json').read_text(encoding='utf-8')):
    QUESTIONS.append(Question(item['id'],item['area'],item['subject'],item['prompt'],tuple(item['options']),item['answer'],item['explanation'],item['source'],tuple(item['alternative_explanations'])))
BY_ID = {q.id: q for q in QUESTIONS}
