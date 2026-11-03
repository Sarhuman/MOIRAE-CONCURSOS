# Correção automatizada — integração controlada, desativada por padrão

## Estado

Implementados: adaptador HTTP da OpenAI Responses API com saída estruturada, validação local, fila SQLite persistente, lease com token, controle transacional de créditos, endpoints autenticados, página /redacoes-ia e evolução por competência. A oficina /redacoes continua demonstrativa e separada.

Não foi feita chamada real à OpenAI. Modelo não escolhido automaticamente; credencial não criada nem configurada. Testes usam modelo, chave e respostas sintéticos. Não houve calibração pedagógica com referência humana. O mecanismo é implementado; o serviço não está liberado para alunos ou vendas.

## Configuração e operação

Manter MOIRAE_ESSAY_AI=false e MOIRAE_ESSAY_AI_REVIEWED=false. O segundo sinalizador só deve ser alterado depois de avaliação documentada da rubrica, privacidade, devolutivas e operação. É uma trava operacional, não certificação automática. MOIRAE_ESSAY_MODEL exige ID explícito e validado. OPENAI_API_KEY fica exclusivamente no ambiente privado do worker, nunca no Git, frontend, logs ou texto de suporte.

API e worker precisam compartilhar o mesmo MOIRAE_DB de instância única. Executar explicitamente `python -m backend.moirae.essay_worker --once` para um ciclo ou sem --once para loop. O worker recusa execução sem ambas as travas, banco explícito, credencial e modelo. MOIRAE_ESSAY_DAILY_CALLS limita chamadas por dia UTC (padrão 20, permitido 1–100); não é orçamento monetário. Nenhuma chamada de teste externa foi executada nesta entrega.

Não executar múltiplos hosts sobre arquivo SQLite. Produção exige infraestrutura persistente, supervisão, backup/restauração e migração PostgreSQL com testes de concorrência equivalentes.

## Contrato e privacidade

POST /api/essay-evaluations aceita tema, texto, chave UUID e confirmação explícita de processamento externo. Exige aluno verificado, termos e plano ativo; CSRF, origem, tamanho e rate limit existentes. Até um envio pendente por aluno. Conta/nota/créditos não vêm do navegador. A transação guarda texto original, concessão, modelo, versões de rubrica/prompt e aviso externo, enfileira e reserva uma unidade.

GET /api/essay-evaluations lista até 100 envios próprios. GET /api/essay-evaluations/{id} retorna apenas o envio do proprietário. /evolution agrupa até 100 conclusões por modelo/rubrica/prompt e mostra as cinco competências. Demonstrações, falhas e versões diferentes não são misturadas. Variação de estimativa, especialmente entre temas diferentes, não comprova evolução pedagógica.

A página identifica estimativa experimental, ausência de revisão humana e envio à OpenAI. O adaptador pede store=false, sem ferramentas. Isso não equivale a garantia de retenção zero: revisar as condições do provedor e política de dados antes de habilitar. Exportação autenticada inclui textos, resultados, aviso externo versionado e eventos de crédito. Contas com pedidos continuam sujeitas ao bloqueio existente de exclusão até operação de retenção; não contornar esse bloqueio. Não há OCR ou coleta de imagens.

## Créditos e processamento

Schema aditivo 9. Eventos de crédito: reserve +1, consume 0, release -1; chave única por envio/evento e checks de consistência. A soma por concessão é o uso real reservado/concluído. A demonstração não mexe nesse ledger. Sucesso consome uma unidade, falha definitiva libera a reserva uma vez. Não há reserva acima do saldo nem segundo pendente concorrente. Novas correções integrais de reescritas usam novo envio/crédito; a integração ainda não avalia automaticamente trechos reescritos.

Worker usa transação curta para adquirir lease de 120 segundos e depois fecha a transação antes da chamada externa. Só uma lease ativa por banco. Ao concluir, confere token, prazo e validade da concessão. Um worker antigo não pode sobrescrever outro resultado nem devolver crédito de uma correção já concluída. Acesso revogado/expirado descarta o resultado e libera reserva, mesmo se o provedor já tiver cobrado a chamada.

Falhas transitórias de rede/timeout/429/5xx podem tentar novamente até três chamadas, com espera crescente. Recusa, saída incompleta, JSON inválido ou trechos inconsistentes falham sem nota zero inventada. Há limite de saída de 3500 tokens, corpo de 1 MB e timeout de rede; o orçamento de leitura é acompanhado para limitar execução. Falha/interrupção pode deixar a lease expirar para retomada. O processamento é pelo menos uma vez: uma queda após envio remoto pode gerar outra cobrança no provedor. Não se promete exatamente uma chamada externa; o débito ao aluno continua único. Limite diário conta tentativas reservadas, inclusive processos interrompidos.

Se o worker ficar offline ou atingir o limite diário, envios permanecem pendentes com reserva; não há SLA ou reembolso externo automático. Monitorar fila, leases, erros, tentativas e custo antes de liberar. Repetir --once pode ser necessário para recuperar uma lease vencida que atingiu o limite e liberar o próximo item.

## Validação de conteúdo

Rubrica resumida experimental enem-experimental-v1, prompt enem-feedback-v1. As cinco competências devem ser únicas, com notas 0/40/80/120/160/200. O modelo devolve trechos literais; o servidor exige ocorrência única, calcula offsets UTF-16 e rejeita marcações inventadas/ambíguas. A estrutura válida não garante avaliação pedagógica correta. Resultado e devolutivas passam novamente por validação no worker. O navegador usa textContent.

Antes de habilitar: corpus autorizado com avaliações humanas, comparação por competência e desacordo entre avaliadores, falsos apontamentos, temas fora da rubrica, fuga ao tema, instruções maliciosas no texto, vieses, custo/latência e revisão de cada mudança de modelo/prompt. Não existe aprovação pedagógica produzida pelos testes técnicos.

## Conteúdo em preparação

`data/content-drafts/authorial-batch-01.json` adiciona oito questões autorais em rascunho nas quatro áreas, com alternativas e resoluções. publication_allowed=false e revisão editorial pendente; não são itens oficiais nem foram adicionados ao catálogo do aluno. O importador Inep existente continua sendo uma frente separada; esta entrega não resolveu os downloads anteriormente indisponíveis.

## Fontes técnicas oficiais

- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/reference/resources/responses/methods/create

QA visual renderizado e teste real do provedor continuam pendentes. Sem publicação ou merge.
