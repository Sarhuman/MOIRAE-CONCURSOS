# Simulado cronometrado e cota Free mensal

## O que funciona neste piloto

- /simulados usa a mesma autenticação de /estudar.
- Primeiro dia: seis questões autorais introdutórias de Linguagens/Humanas, tema e textos motivadores próprios e redação digitada, com 30 minutos compartilhados.
- Segundo dia: seis questões autorais de Matemática/Natureza, com 15 minutos.
- Não são cadernos oficiais, não reproduzem duração/dificuldade/quantidade do ENEM e não incluem TRI. Os PDFs oficiais continuam pendentes.
- Cartão-resposta com navegação, indicação de respondidas e marcações de revisão.
- Respostas salvas ao selecionar alternativas ou marcar revisão, com confirmação. É possível alterar respostas dentro do prazo, sem novo consumo.
- Redação com até 4.000 caracteres, salvamento após pausa na digitação e botão de salvamento explícito. Esse limite é técnico para o piloto, não uma equivalência a linhas oficiais.
- Retomada preserva respostas, redação e deadline. O prazo não pausa ao recarregar, mudar de aba ou sair.
- Encerramento manual com confirmação; o servidor rejeita alterações a partir do deadline e apresenta o resultado após encerramento/expiração.
- O Free vê só a tentativa mais recente, sem consulta ao histórico de simulados. Não há dashboard de evolução.
- A redação fica salva, sem correção ou nota. Nenhuma chamada à OpenAI.

## Regra comercial implementada

30 questões por mês no Free, compartilhadas entre prática e simulados. O saldo renova à meia-noite do primeiro dia do mês em America/Sao_Paulo, sem acumular. O painel informa usado, disponível e data de renovação.

Na prática, cada nova resposta aceita conta uma unidade; revisitar a explicação não conta. No simulado, o caderno inteiro é descontado ao iniciar (seis unidades nesta versão), inclusive se o aluno abandonar ou deixar tudo em branco. A interface informa a regra e pede confirmação antes de começar. Assim não é possível abrir múltiplos cadernos para contornar o limite. Alterações, reenvios e retomadas do mesmo simulado não descontam novamente.

O aluno precisa ter saldo para o caderno inteiro. Se tiver menos de seis unidades, ainda pode usar o saldo restante em exercícios. Não há venda ou mudança de plano implementada.

Uma tentativa que cruza a virada do mês continua vinculada à cota do mês em que começou: nenhuma segunda cobrança ao responder depois da virada. O mês novo começa com saldo novo, sem transportar saldo anterior.

## Integridade

BEGIN IMMEDIATE serializa a leitura do saldo e o início de simulado ou resposta de prática. O saldo é calculado pelas tentativas existentes mais os cadernos debitados do período; não há contador confiado ao navegador. As respostas antigas do piloto diário são preservadas e passam a contar no seu mês de registro.

A chave de início é única por aluno; repetir a solicitação retorna a mesma tentativa, mesmo após terminar. Existe no máximo um simulado ativo por aluno. O servidor define conteúdo e duração: o cliente não envia nem escolhe um deadline. Caderno, respostas e redação são isolados pelo usuário autenticado.

As revisões numéricas de respostas e redação evitam sobrescrita silenciosa entre abas. Reenvios idênticos são aceitos sem alteração. Em conflito, a interface pede para copiar o rascunho e atualizar.

O relógio visual usa server_now, deadline e tempo monotônico do navegador. O deadline do servidor é a autoridade, independentemente do relógio do computador. O navegador sincroniza periodicamente e ao voltar para a aba. Há aviso nos cinco minutos finais.

A expiração é materializada na próxima requisição (leitura, salvamento, novo início ou entrega); não depende de um agendador em segundo plano para bloquear escrita tardia. Não há tolerância extra para mensagens que chegam depois do prazo. O último rascunho salvo é preservado. Se ainda houver texto não enviado no navegador, ele é exibido separadamente para cópia, sem passar a integrar o texto entregue. Não há upload manuscrito ou OCR nesta entrega.

## Verificar

```sh
.venv/bin/python -m pytest -q
node --check web/exam.js
node --test tests/essay-fixture.test.cjs
```

Testes cobrem consumo compartilhado, renovação mensal, meia-noite de Brasília, corrida prática/simulado, início concorrente, retry, respostas alteradas, bloqueio de abas desatualizadas, redação persistente após reinício, isolamento, limite de tamanho e bloqueio exato do deadline.

QA manual no navegador autenticado permanece pendente pela limitação da prévia Python deste ambiente. Validação HTTP não substitui essa etapa. Executar o backend localmente e verificar login, escolha do treino, confirmação de débito, respostas, marcação, autosave, retomada e entrega em desktop e celular antes de lançar.

## Próximas etapas

Questões oficiais revisadas, perfis de prova completa alinhados à edição do exame, aprovação dos direitos premium, correção OpenAI com créditos, controles de lançamento e backend de produção. O site estático hospedado pode mostrar os planos atualizados, mas não serve esta API Python.
