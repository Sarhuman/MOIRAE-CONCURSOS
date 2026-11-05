# Triagem operacional de pedidos — somente leitura

Base desta rodada: `1be6b75`, PR #8 em draft. A CI dessa base foi conferida e estava aprovada em Windows, Ubuntu e frontend. O ciclo financeiro interno sandbox v10 foi reutilizado, sem segundo ledger, worker ou reconciliador de pagamento.

## Entrega

`backend.moirae.order_review` permite inventariar pedidos em análise e solicitações de reembolso registradas, ou inspecionar um pedido específico. Abre um banco **já existente** com `mode=ro` e `query_only`, dentro de uma transação de leitura para um snapshot consistente. Não instancia `Store`, não migra schema, não executa expiração/cancelamento e não chama provedor. Requer schema 15 existente e não acrescenta nova versão de banco.

Não existe endpoint HTTP novo, aprovação manual, concessão, estorno ou liberação automática. A ferramenta não transforma um diagnóstico em autorização para resolver o pedido.

## Inventário dos casos

| Caso observado | Evidência a conferir | Decisão que continua necessária |
| --- | --- | --- |
| Resposta incerta na criação de preferência | Preferência e pagamento pela referência original do pedido, situação no provedor | Confirmar ausência ou existência do pagamento antes de outra tentativa; não criar preferência duplicada |
| Pagamento após fim/cancelamento da reserva | Horários do pagamento e encerramento local; histórico do cupom | Decidir tratamento do valor recebido sem reutilizar reserva liberada |
| Outro acesso ativo na confirmação | Períodos já concedidos e contrato do novo pedido | Regra de acumulação, remarcação ou devolução; sem prolongamento automático |
| Reembolso parcial ou crédito consumido | Valor pago/devolvido, consumo, lotes e reservas | Política monetária aprovada; não converter créditos consumidos em valor de estorno automaticamente |
| Estado do provedor regrediu após concessão | Estado/versão consultados e bloqueios atuais | Investigar a divergência preservando o bloqueio |
| Cupom indisponível na liquidação | Titularidade, validade, campanha e histórico de reserva/resgate | Não recriar cupom nem capacidade para forçar concessão |
| Solicitação de reembolso registrada | Pedido e situação financeira atual | Registro da solicitação não comprova estorno ou aprovação monetária |
| Motivo ausente/desconhecido | Inspeção local autorizada do contrato e evidências | Não presumir que o pedido pode ser liberado |

Pedidos legados podem ter `needs_review` sem contrato/motivo estruturado; a ferramenta indica caso não classificado, sem inventar diagnóstico. Não reproduz texto livre de `review_reason`, exceções ou snapshots brutos no JSON.

## Executar no Windows

No PowerShell, na pasta da cópia isolada, com `.venv-win` já preparada:

```powershell
.\.venv-win\Scripts\python.exe -m backend.moirae.order_review --database "$env:MOIRAE_DB"
```

Para um pedido específico, substitua pelo UUID real do pedido:

```powershell
.\.venv-win\Scripts\python.exe -m backend.moirae.order_review --database "$env:MOIRAE_DB" --order 'UUID-DO-PEDIDO'
```

O exemplo com `UUID-DO-PEDIDO` é um marcador: a ferramenta recusa identificador inválido. Para limitar a listagem:

```powershell
.\.venv-win\Scripts\python.exe -m backend.moirae.order_review --database "$env:MOIRAE_DB" --limit 50
```

Limite padrão 100, permitido 1–1000. `total_matching`, `returned` e `has_more` tornam explícito quando a listagem foi truncada. Inspeção específica aceita pedido sem sinalização e informa `not_flagged`/`inspection_only`, sem inventar pendência.

O relatório não contém e-mail, ID do titular, URL de checkout, código de cupom, ID do pagamento ou JSON bruto do contrato. Traz somente o identificador do pedido, produto/estados conhecidos, valores numéricos, presença de pagamento vinculado, contadores do lote, situação do hold e evidências necessárias. Não publique o relatório: IDs e valores ainda são dados operacionais. Não use redirecionamento da saída para arquivo público ou commit de relatórios reais.

## Inconsistências sinalizadas, sem reparo

Snapshot inválido, moeda/valor/aritmética divergentes, lote ausente ou de outro titular, hold de outro titular, lote ainda gastável em caso em análise e hold ativo em análise. Contadores de lote de outra conta não são exibidos. A ferramenta apenas sinaliza; não altera saldo, vínculo ou estado.

Não comprova a correção integral do ledger, a atualidade do pagamento externo ou a conclusão de uma solicitação. Não expira contratos pendentes por conta própria; isso pertence ao fluxo financeiro já existente.

## Procedimento operacional antes de qualquer resolução futura

1. Registrar internamente o pedido/caso e o responsável pela revisão, sem publicar dados no Git.
2. Executar a triagem de leitura e conferir contrato, lote, cupom e presença de evidência de pagamento.
3. Quando houver acesso sandbox autorizado, conferir o pagamento no provedor pela referência original, sem confiar no navegador ou em retorno de checkout.
4. Distinguir decisão técnica de decisão comercial/monetária; manter o caso bloqueado quando faltar política.
5. Registrar a decisão e suas evidências em local de acesso restrito. Nenhuma anotação ou relatório de triagem concede crédito.
6. Uma futura ação de resolução exigirá autorização de operador, versão do estado esperado, idempotência, auditoria e reconciliação com o provedor. Esses comandos de escrita não foram implementados nesta entrega.

## Verificações e bloqueios

Testes cobrem ausência de mutação, bloqueio de escrita, timeout sem chamada externa, pagamento tardio, consumo/reembolso, motivos/snapshots inválidos, isolamento de contadores, paginação, banco inexistente/legado e caminhos com espaços/acentos no padrão Windows.

Neste ambiente de execução foi verificada somente a **presença** de configuração: token, coletor, segredo do webhook, origem HTTPS e validade dos pacotes estavam ausentes. Não foram impressos valores de segredo. Isso não descreve o computador ou a conta Mercado Pago do Henrique. Homologação externa continua pendente.

Validação visual real continua pendente; não foi tentado contorno do bloqueio descrito pelo Codex e não foram produzidas capturas novas. O roteiro visual de Windows permanece em `sandbox-orders-v10.md`/`windows-wallet-validation-v9.md`. Sem chamadas OpenAI, campanha operacional, merge, deploy ou cobrança real.

Validação local desta entrega: **245 testes Python e 16 testes JavaScript aprovados**, incluindo dez testes novos de triagem; sintaxe web e compilação Python aprovadas. Ambiente local desta rodada é o executor, não o Windows do Henrique. O aviso de depreciação TestClient/HTTPX foi mantido. Confira a CI do novo HEAD separadamente para a execução Windows/Ubuntu.
