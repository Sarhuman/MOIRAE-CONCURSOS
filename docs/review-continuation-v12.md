# Revisão da main e continuidade — 05/11/2026

## Avaliação da entrega anterior

A main conferida foi `14fa542d05e94ed9e0614062803f3d1adeee2f01`, posterior à referência informada `61447d3`: inclui a consolidação do PR #8 e o pacote de validação do PR #9. A [CI da base](https://github.com/Sarhuman/MOIRAE-CONCURSOS/actions/runs/42044882977) estava aprovada: 256 Python em cada backend e 16 JavaScript. Não somar plataformas como testes diferentes.

A organização documental, a triagem local e os resumos da CI preservam os limites do piloto. A triagem usa conexão SQLite somente leitura e snapshot transacional, omite texto livre/segredos e não consulta provedor. O gerador de resumos conta cada testcase uma vez, limita XML e não converte relatório ausente/ignorado em aprovação. Os 21 testes originais desses dois módulos passaram na revisão local.

Foram encontrados e corrigidos falsos negativos na triagem e a perda visual do resultado após recarregar a área de estudo. A avaliação não equivale a aprovação comercial ou homologação externa.

## Correções comprovadas

### Triagem somente leitura

Oito reproduções sintéticas falharam antes da correção: contrato de outro titular; desconto ausente; preço em tipo inválido; quantidade zero; validade booleana; pacote concluído sem lote; reservado sem reserva correspondente; consumido sem consumo correspondente. Esses casos não eram sinalizados na inspeção específica.

Agora a ferramenta sinaliza as inconsistências e omite snapshot/lote quando o contrato pertence a outro titular. Contadores são comparados às reservas já existentes, sem criar ledger paralelo. Nove casos novos incluem também um ciclo legítimo de reservar, consumir, devolver, liberar e revogar, para evitar falsos alarmes. Os testes comparam o dump antes/depois e preservam o bloqueio de escrita.

A listagem padrão continua restrita a casos já sinalizados ou solicitações de reembolso. `--order` permite conferir um pedido específico sem sinalização prévia. Não foi implementada varredura integral de todos os pedidos, resolução automática, novo schema, aprovação administrativa ou reparo de saldo.

### Conclusão da atividade

Na navegação real, as cinco respostas terminavam corretamente e não reiniciavam na primeira questão, mas a recarga descartava o resumo: `/practice/current` retornava apenas a atividade ativa. A interface já possuía um estado de conclusão que não era recuperado por esse endpoint.

`session` mantém o significado anterior (atividade ativa ou null). O campo aditivo `completed` retorna somente o último resultado concluído do próprio titular quando não existe atividade ativa, incluindo acertos/total. A consulta não cria sessão, tentativa ou débito. A atividade ativa tem prioridade; não foi aberta consulta ao histórico completo do Free.

A interface reapresenta o resultado após recarga e reinício do servidor, acima das opções de novo bloco. Outra atividade exige ação explícita. O teste existente de cinco questões foi reforçado, preservando sua asserção de `session=null`; dois testes adicionais cobrem reinício/prioridade e isolamento entre contas.

Também foram corrigidos espaçamento das ações, texto ambíguo sobre conta Free e mensagens públicas que ainda citavam simulados completos ou carteira em preparação. A página agora distingue os treinos de seis questões, a carteira demonstrativa e a correção real indisponível. Preços e condições comerciais não mudaram.

## Navegação real executada

Depois de uma consulta inicial expirar, o inventário retornou um navegador integrado suportado. O aplicativo FastAPI foi aberto em localhost, usando banco novo com conta sintética verificada, acesso local e três créditos. Não houve interceptação de respostas, fixtures servidas no lugar da API, contorno da proteção anterior ou chamadas a provedores externos.

| Percurso | Evidência observada |
| --- | --- |
| Login e conta | Sessão real da conta de teste e e-mail confirmado |
| Diagnóstico desktop | Cinco questões das quatro áreas, erros/acertos, explicações por alternativa e recomendação persistida |
| Resposta errada | Alternativa correta apresentada com letra **e texto**, incluindo o deslocamento pendular |
| Conclusão/retomada | Resumo ausente antes da correção; preservado após recarga e reinício depois da correção |
| Prática em 360 px | Outro bloco de cinco questões respondido por cliques; recarga mantém conclusão, sem retornar à primeira |
| Carteira/oficina | 3 disponíveis → 2 disponíveis/1 reservado → 2 disponíveis/0 reservado/1 consumido |
| Retomada da redação | Envio reaberto pelo histórico antes de gerar a demonstração; notas fixas e crédito consumido uma vez; saldo estável após recarga |
| Planos | R$44/R$110, 10/30 previstos, pedido sintético próprio e checkout desabilitado |
| Teclado | Diálogo de análise: foco inicial na senha, Tab/Shift+Tab dentro do diálogo, Escape fecha e devolve foco ao botão de origem |
| Roleta | Giro demonstrativo, mensagem de nenhum cupom emitido, fechamento por Escape e retorno de foco; sem campanha operacional |

As respostas são deliberadamente de teste, sem medir desempenho pedagógico. Nenhuma solicitação monetária foi enviada pelo diálogo; apenas abertura, foco e fechamento foram testados.

Sete páginas (`/`, `/conta`, `/estudar`, `/diagnostico`, `/planos`, `/carteira`, `/redacoes`) foram renderizadas em desktop e em 360/390/430 px: **28 medições sem overflow horizontal da página**, conforme [medidas capturadas do DOM](evidence/v12/responsive-metrics.json). Há capturas completas na pasta local `outputs/moirae-main-review-2026-11-05`. Os dados sintéticos foram persistidos pelo backend real.

Capturas selecionadas, sem edição ou simulação:

- [Conclusão no desktop](evidence/v12/desktop-completed.jpg).
- [Conclusão em 360 px](evidence/v12/mobile-360-completed.jpg).
- [Roleta demonstrativa em 390 px](evidence/v12/roulette-390.jpg).

Capturas podem incluir foco/link de pulo visível durante a interação. Emulação não equivale a celular físico e ausência de overflow não comprova acessibilidade integral.

## Verificações automatizadas

- Base: 21 testes de triagem/resumos aprovados em 51,36 s.
- Antes da correção: oito reproduções de triagem falharam e três verificações da conclusão falharam; os logs foram preservados como evidência das causas.
- Após a correção da triagem: 29 selecionados aprovados em 73,37 s; o caso adicional de ciclo legítimo integra a suíte completa.
- Após a correção da conclusão: todos os 24 testes de prática aprovados em 229,28 s.
- CI do código `5045432`: [execução 42117105871](https://github.com/Sarhuman/MOIRAE-CONCURSOS/actions/runs/42117105871), **267 Python aprovados** no Ubuntu (28,09 s) e Windows (117,45 s), frontend aprovado.
- JavaScript: 16 aprovados; sintaxe dos 19 scripts e compilação de backend/scripts aprovadas. Aviso conhecido TestClient/HTTPX mantido.
- Suíte local completa da fase de triagem, correspondente ao código `5dfc33e`: **265 aprovados em 1110,64 s**, Windows nativo/Python 3.13.14. O complemento da conclusão foi exercitado nos 24 testes de prática e na CI completa com 267 casos. Não somar seleções sobrepostas aos totais completos.

## Pendências preservadas

**QA visual ainda parcial.** Atalhos de zoom no navegador integrado não alteraram a escala observada; 200% não foi validado. A preferência de movimento reduzido estava desativada e não foi alterada. Celular físico, auditoria completa de contraste/leitor de tela, falhas de conexão por UI e todos os percursos de revisão/simulados continuam para conferência manual. Não marcar o checklist inteiro como aprovado por causa das capturas desta rodada.

Homologação Mercado Pago externa, validade/termos dos pacotes, datas/limite da campanha, política monetária de créditos consumidos/devoluções parciais, resolução autorizada, e-mail/backup de produção e avaliação da correção real continuam pendentes. Não houve alteração de campanhas, chamada OpenAI, cobrança real, merge ou deploy. Os checkouts anteriores e bancos existentes foram preservados; nova branch baseada na main, PR em draft.

## Conferência Windows

1. Atualize uma cópia limpa da branch deste PR ou use checkout isolado. Preserve alterações/bancos existentes.
2. Prepare `.venv-win` e um banco novo conforme README; não reaproveite banco de aluno para QA.
3. Para carteira, habilite somente `MOIRAE_ESSAY_DEMO` e `MOIRAE_COMMERCE_SANDBOX`; mantenha Mercado Pago e ambas as flags de IA desativados. Use `local_playtest --wallet-credits 3` em arquivo novo.
4. Inicie `uvicorn backend.moirae.app:create_app --factory` com a origem/porta configuradas e faça login na conta preparada.
5. Termine cinco questões, atualize e reabra: resultado permanece; outro bloco só começa por escolha explícita.
6. Envie redação pela carteira, confira reserva, gere demonstração e atualize: saldo 2/0/1, sem consumo duplicado.
7. Confira desktop/360/390/430 px, depois faça os itens ainda pendentes de zoom 200%, movimento reduzido e celular físico. Registre o ambiente e capturas reais.
8. Reproduza os testes com `python -m pytest -q` na venv Windows e os testes Node conforme README; a triagem CLI permanece somente leitura.
