# Documentação do MOIRAE

Este índice separa o estado atual dos registros de entregas anteriores. O piloto integrado à `main` continua local/sandbox; páginas históricas podem mencionar branches, preços ou limitações já substituídos.

Experiência atual: [cadastro, login e área do aluno v14](account-experience-v14.md).

Regra atual: [questões somente após cadastro v13](registered-access-v13.md). Revisão e evidências anteriores: [v12](review-continuation-v12.md).

## Começar e testar

[Pacote de validação pelo GitHub](validation-package.md): relatórios automáticos, checklist manual e formulário de problemas, sem comandos no PC do trabalho.

| Documento | Finalidade |
| --- | --- |
| [README principal](../README.md) | Estado do produto, preços, instalação Windows e limites |
| [Desenvolvimento](../DEVELOPMENT.md) | Backend versus prévia estática e verificações |
| [Próximo teste local](next-local-test.md) | Preparo local e cuidado com bancos/contas existentes |
| [Validação Windows v9](windows-wallet-validation-v9.md) | Roteiro manual e registro do bloqueio de navegador |
| [Carteira/oficina v7](wallet-essay-flow-v7.md) | Primeiro percurso completo com três créditos de teste |

## Contratos e operação atuais

| Documento | Finalidade |
| --- | --- |
| [Pedidos sandbox v10](sandbox-orders-v10.md) | Fonte atual do ciclo interno pedido, pagamento verificado, lote e cupom |
| [Triagem v11](order-review-v11.md) | Inventário local somente leitura de casos em análise |
| [Política de cupom v8](coupon-policy-v8.md) | 5%, 1/100, três meses e Avançado, sem campanha operacional |
| [Billing sandbox](billing-sandbox.md) | Configuração do adaptador, validações e limites de homologação |
| [Correção real](real-essay-evaluation.md) | Fila/worker separados, travas e avaliação pedagógica pendente |
| [Conta e privacidade](accounts-privacy.md) | Conta local, tokens, exportação e exclusão |
| [Revisão espaçada](study-planner.md) | Planejamento determinístico e agendamento |
| [Caderno](review-notebook.md) | Erros/favoritos e permissões |
| [Simulados](timed-exams.md) | Duração, cota e retomada dos treinos reduzidos |
| [Importação INEP](inep-import.md) | Proveniência, revisão e acervo separado de itens interativos |

## Histórico e propostas

`competitive-plan.md`, `portfolio-commerce-v4.md`, `review-fixes-v5.md`, `sandbox-commerce-v6.md` e `wallet-essay-flow-v7.md` documentam decisões e entregas anteriores. Leia seus avisos de atualização e o estado financeiro v10 antes de implementar algo descrito como pendente no passado. Valores de exemplo em testes e datas/limites de fixtures não são aprovação comercial.

O prompt `codex-remaining-v5.md` é histórico. A continuidade deve começar pela `main` atual, este índice, `sandbox-orders-v10.md` e `order-review-v11.md`. Não reabrir trabalhos já concluídos apenas porque um documento antigo dizia que eram futuros.

## Consolidação e próximos bloqueios

[Registro da integração na main](main-consolidation.md). Continuam pendentes QA visual real, homologação externa Mercado Pago, decisões comerciais/monetárias, operação de resolução, e-mail de lançamento e avaliação da correção real. Não há autorização implícita de produção por causa da integração do código.
