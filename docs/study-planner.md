# Planejamento e revisão espaçada — piloto local

## Ciclo entregue

Toda resposta de prática aceita passa a atualizar uma agenda transacional. Erro agenda nova revisão em 24 horas e reinicia o estágio. Acertos posteriores em questões com erro prévio avançam pelos intervalos de 3, 7, 14 e 30 dias (teto de 30). Acerto sem erro anterior não cria revisão de recuperação. Reenvio idempotente não altera agenda nem duplica tentativa. Uma nova tentativa intencional, inclusive na prática livre, atualiza a agenda mesmo antes do vencimento.

Schema aditivo 8 cria `review_schedule` e `practice_plans`, com exclusão em cascata. A migração inicial considera a resposta mais recente de cada questão que teve erro: 1 dia após erro ou 3 após acerto recente. Não inventa uma sequência histórica de domínio. Executada uma única vez e preservada em reinícios.

## Próxima ação

GET `/api/planner?minutes=15|30|60` exige plano pago ativo, conta verificada e termos aceitos. Prioridade determinística: revisões vencidas pela data mais antiga; assuntos com erros pela proporção de acertos; questões ainda não praticadas; consolidação. Questões com revisão futura são excluídas da seleção. O painel informa os motivos, quantidade vencida e próxima data futura. Somente dados do próprio aluno são consultados.

Blocos de 15/30/60 minutos selecionam até 3/6/12 questões, limitados às elegíveis no catálogo autoral. O tempo inclui responder, ler e revisar, não é previsão calibrada nem deadline. Os limites não são uma promessa de equivalência ao tempo de prova.

POST `/api/planner/start` recebe apenas `minutes`, com origem/CSRF/rate limit. O servidor escolhe e persiste questões e motivos na mesma transação. Uma sessão ativa é retomada, sem substituição por outro bloco. Repetir ou concorrer no início não cria sessões paralelas. Sem questões elegíveis, responde 409 sem sessão vazia; prática livre continua disponível separadamente.

A execução usa o fluxo existente questão a questão: sem gabarito no payload antecipado, propriedade validada, idempotência e consumo de cota vigente a cada resposta. Consulta ao plano não consome cota. Se o plano vencer, novas recomendações/inícios planejados ficam bloqueados; sessão existente segue as regras Free da prática e sua cota. Histórico e agenda são preservados. Exportação inclui agenda e descrições das sessões planejadas.

## Limites

Somente prática: simulados e redações não entram nesta agenda. Planejamento é uma regra simples explicável, sem IA, calibração pedagógica ou previsão de nota. Agenda calcula intervalos em horas decorridas; a interface exibe datas no horário de Brasília. Não é automação de notificações externas. Sem alteração de preços, venda ou publicação.

Revisão visual renderizada permanece pendente; a falha anterior no download do Chromium não foi resolvida por esta entrega.

## Verificação

Testes de intervalos, reinício por erro, teto, prioridade, futuro excluído, 15/30/60, retomada, concorrência, ausência de gabarito, acesso/vencimento, CSRF, entradas inválidas, privacidade, exportação, migração idempotente, ciclo completo erro→revisão→acerto e ausência de sessão vazia. Testes existentes continuam exigidos.
